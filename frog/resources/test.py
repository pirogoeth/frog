# -*- coding: utf-8 -*-

from itertools import zip_longest

from frog.inventory import InventoryItem
from frog.result import ExecutionResult


def ping(*, message: str="pong") -> str:
    """ Dumb ping on a host.
    """

    return ExecutionResult.ok(message=message)