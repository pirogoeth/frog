# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Mapping, Optional

from frog import context
from frog.inventory import InventoryItem
from frog.util.dictser import DictSerializable


class ExecutionResult(DictSerializable):
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

    def __init__(self, host: InventoryItem, success: Optional[Mapping[str, Any]]=None, failure: Optional[Mapping[str, Any]]=None):
        if not success and not failure:
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