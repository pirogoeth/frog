# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import os
import pathlib
import subprocess
import sys
import threading
from collections import deque
from typing import Any, Callable, Iterable, List, Mapping, Optional

from mitogen.core import CallError, Context, StreamError
from mitogen.master import Broker, Router
from mitogen.select import Select
from mitogen.service import FileService, get_or_create_pool

from frog import context, facts, package_root
from frog.errors import ConnectionError
from frog.fact_cache import FactCache, MemoryFactCache
from frog.inventory import Inventory, InventoryItem
from frog.remoteenv import bootstrapper
from frog.util.dictser import DictSerializable

logger = logging.getLogger(__name__)


class Runner:

    def __init__(self):
        self._broker = Broker()
        self._router = Router(broker=self._broker)
        self._connections = {}

        self._file_service = FileService(self._router)
        self._file_service.register_prefix(package_root())

        self._pool = get_or_create_pool(router=self._router)
        self._pool.add(self._file_service)

        self.bootstrap_settings = None
        self.fact_cache = MemoryFactCache()

    __all__ = ["execute", "close", "gather_facts", "execute_on_host"]

    def register_fs_prefix(self, prefix: str):
        self._file_service.register_prefix(prefix)

    def gather_facts(self, hosts: Inventory, fact_cache: Optional[FactCache]=None):
        _fact_cache = fact_cache or self.fact_cache
        logger.debug(f"Gathering via {_fact_cache}")

        for host in hosts:
            try:
                host.update_facts(_fact_cache.get(host.host))
            except FactCache.NeedsUpdate:
                logger.debug(f"Host {host.host} fact cache data is invalid, updating")

                subset = hosts.select(host.host)
                result = self.execute(subset, "facts.gather").pop()
                host = result["host"]
                facts = result["result"]
                host.update_facts(facts)
                _fact_cache.update(host.host, facts)

    def execute(self, hosts: Inventory, target: str, kw: Optional[dict]=None) -> Iterable[ExecutionResult]:
        if kw is None:
            kw = {}

        results: Iterable[ExecutionResult] = deque([])
        pool = []
        for item in hosts:
            logger.info(f"Enqueue host {item.host} to run {target}({kw})")
            # Create a new local context for each of the hosts we should run on
            # TODO: Ideally, chunk this out into more reasonable, parallelizable chunks.
            child = threading.Thread(
                name=f"runner[{item.host}]",
                daemon=True,
                target=self.execute_on_host,
                args=(results, item, hosts, target),
                kwargs={"kw": kw},
            )
            child.start()
            pool.append(child)

        while True:
            if not pool:
                # Pool's closed, go away
                break

            done_idxs = []
            for idx in range(len(pool)):
                thread = pool[idx]
                thread.join(timeout=1)
                if not thread.is_alive():
                    done_idxs.append(idx)

            for idx in reversed(done_idxs):
                pool.pop(idx)

        return results

    def get_or_create_connection(self, item: InventoryItem) -> Context:
        if str(item) in self._connections:
            return self._connections[str(item)]

        try:
            ctx = item.open_connection(self._router)
            ctx = self.into_bootstrap(ctx)
            self._connections[str(item)] = ctx
            return ctx
        except StreamError as err:
            raise ConnectionError(item).with_cause(err)

    def into_bootstrap(self, ctx: Context) -> Context:
        """ Wraps a connection context into another connection
            context inside of a bootstrapped venv.
            If the venv is not available, it will be created.
        """

        bin_path = ctx.call(bootstrapper.bootstrap, self._router.myself(), self.bootstrap_settings)
        return self._router.local(
            python_path=[bin_path],
            via=ctx,
        )

    def execute_on_host(self, results: deque, item: InventoryItem, source: Inventory, target: str, kw: Optional[dict]=None):
        ctx = self.get_or_create_connection(item)
        payload_args = (
            source.serialize(deepcopy=True),  # the inventory the host was sourced from
            item.serialize(deepcopy=True),    # the details about the host itself
            ctx,                              # the remote host's context
            self._router.myself(),            # the parent/controller's context
            target,                           # the resource function to call
        )

        try:
            results.append(ExecutionResult.ok(
                item.host,
                changed=ctx.call(
                    context.call_with_context, # creates a "context" module the remote can pull info from
                    *payload_args,             # arguments specifically describing the where, whomst'd've, and what of the call
                    **kw,                      # arguments to the resource function
                ),
            ))
        except CallError as err:
            if "cannot unpickle" in str(err):
                logger.exception(f"Error unpickling payload (target={target}, item={item}) (args={payload_args}, kw={kw})")
            else:
                results.append(ExecutionResult.fail(item.host, err))
        except Exception as err:
            logger.exception(f"Unhandled exception during call to {item}")
            results.append(ExecutionResult.fail(item.host, err))

    def close(self):
        self._pool.stop()
        self._broker.shutdown()
        self._broker.join()


class ExecutionResult(DictSerializable):

    host: str
    success: Optional[Mapping[str, Any]] = None
    failure: Optional[Mapping[str, Any]] = None

    @classmethod
    def ok(cls, host: str, **kw) -> ExecutionResult:
        return ExecutionResult(host, success=kw)

    @classmethod
    def fail(cls, host: str, exc: Exception) -> ExecutionResult:
        return ExecutionResult(host, failure={
            "exception": type(exc).__name__,
            "repr": repr(exc),
            "args": exc.args,
        })

    def __init__(self, host: str, success: Optional[Mapping[str, Any]]=None, failure: Optional[Mapping[str, Any]]=None):
        if not success and not failure:
            raise ValueError("Either `success` or `failure` is required")

        self.host = host
        self.success = success
        self.failure = failure

    def asdict(self):
        out = {"host": self.host}
        if self.success:
            out["success"] = self.success
        elif self.failure:
            out["failure"] = self.failure

        return out

    def outcome(self) -> Optional[Mapping[str, Any]]:
        return self.success or self.failure