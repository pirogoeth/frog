# -*- coding: utf-8 -*-

from __future__ import annotations

import functools
from typing import Any, Callable, Iterable, List, Mapping, Optional

from frog import context
from frog.inventory import InventoryItem
from frog.util.dictser import DictDeserializable, DictSerializable


class ExecutionResult(DictSerializable, DictDeserializable):
    """ ExecutionResult is the result of an execution of a resource or cookbook.
        These results should be returned by each function and can be as descriptive
        as the bottom-level resource or cookbook wishes to be, as long as a success or a fail
        are provided.
    """

    _host: InventoryItem
    _success: Optional[Mapping[str, Any]] = None
    _failure: Optional[Mapping[str, Any]] = None

    @classmethod
    def ok(cls, host: Optional[InventoryItem]=None, **kw) -> ExecutionResult:
        if host is None:
            host = context.host

        return ExecutionResult(host, success=kw)

    @classmethod
    def fail(cls, exc: Exception, host: Optional[InventoryItem]=None, **kw) -> ExecutionResult:
        if host is None:
            host = context.host

        return ExecutionResult(host, failure=dict(
            exception={
                "name": type(exc).__name__,
                "repr": repr(exc),
                "args": exc.args,
            },
            **kw
        ))

    @classmethod
    def deserialize(cls, data: dict) -> ExecutionResult:
        if "results" in data:
            return ResultChain.deserialize(data)

        print(data)

        return cls(
            host=InventoryItem.deserialize(data["host"]),
            success=data.pop("success", {}),
            failure=data.pop("failure", {}),
        )

    def __init__(self, host: InventoryItem, success: Optional[Mapping[str, Any]]=None, failure: Optional[Mapping[str, Any]]=None):
        if not any((success, failure,)):
            raise ValueError("Either `success` or `failure` is required")

        self._host = host
        self._success = success
        self._failure = failure

    @property
    def host(self) -> InventoryItem:
        return self._host

    def asdict(self):
        out = {"host": self._host}
        if self._success:
            out["success"] = self._success
        elif self._failure:
            out["failure"] = self._failure

        return out

    def outcome(self) -> Optional[Mapping[str, Any]]:
        return self._success or self._failure

    def outcome_list(self) -> List[Mapping[str, Any]]:
        return [self.outcome()]

    def unwrap(self) -> Mapping[str, Any]:
        if self._success:
            return self._success
        else:
            exc = self._failure
            raise Exception(f"Captured exception: {exc['name']} {exc['repr']}")


class ResultChain(DictSerializable, DictDeserializable):
    _host: InventoryItem
    _results: List[ExecutionResult]

    @classmethod
    def deserialize(cls, data: dict) -> ExecutionResult:
        if "host" in data and any(["success" in data, "failure" in data]):
            return ExecutionResult.deserialize(data)

        from pprint import pformat
        print(f"deserialize ResultChain {pformat(data)}")

        return cls(
            host=InventoryItem.deserialize(data["host"]),
            results=[ResultChain.deserialize(result) for result in data.pop("results", [])],
        )

    def __init__(self, host: Optional[InventoryItem]=None, results: Optional[List[ExecutionResult]]=None):
        if host is None:
            host = context.host

        self._host = host
        self._results = results or []

    @property
    def host(self) -> InventoryItem:
        return self._host

    def chain(self, result: ExecutionResult):
        self._results.append(result)

    def outcome(self) -> Optional[Iterable[Mapping[str, Any]]]:
        for result in self._results:
            yield result.asdict()

    def outcome_list(self) -> List[Iterable[Mapping[str, Any]]]:
        return list(self.outcome())

    def asdict(self):
        return {"host": self.host, "results": self._results}


ResourceFn = Callable[..., ExecutionResult]


def thunk(fn: ResourceFn) -> ResourceFn:
    """ Wraps a resource function into an ExecutionThunk. """

    @functools.wraps(fn)
    def inner(*args, **kw):
        return ExecutionThunk(fn, *args, **kw)

    return inner


class ExecutionThunk:
    """ ExecutionThunk wraps a resource/chain of resources and turns it into a
        deferrable, chainable action.
    """

    def __init__(self, fn: ResourceFn, *args, **kw):
        self._resources = []
        self._resources.append(functools.partial(fn, *args, **kw))

    def then(self, next_thunk: ExecutionThunk) -> ExecutionThunk:
        self._resources.extend(next_thunk._resources)
        return self

    def execute(self) -> ResultChain:
        """ Executes a series of wrapped resources, returning a single
            ExecutionResult of the chain.
        """

        final_result = ResultChain()
        for resource in self._resources:
            final_result.chain(resource())

        return final_result
