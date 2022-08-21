# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional


class ConnectionError(Exception):
    def __init__(self, host: InventoryItem):
        super().__init__(self)
        self._host = host
        self._cause: Optional[Exception] = None

    def __repr__(self):
        return f"Error connecting to {self._host.host}: {self._cause or 'unknown'}"

    __str__ = __repr__

    def with_cause(self, cause: Optional[Exception]) -> ConnectionError:
        self._cause = cause

        return self