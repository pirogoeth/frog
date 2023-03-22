# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
from typing import Any
from mitogen.core import Context

from frog import resources
from frog.inventory import Inventory, InventoryItem
from frog.execution import ExecutionResult

context: Context = None
host: InventoryItem = None
inventory: Inventory = None
parent: Context = None


def call_with_context(_inventory: dict, _host: dict, _context: Context, _parent: Context, target: str, **kw) -> Any:
    global context
    global host
    global inventory
    global parent

    context = _context
    parent = _parent
    # Load the serialized versions of these into their respective classes
    host = InventoryItem.fromdict(_host)
    inventory = Inventory.fromdict(_inventory)

    # Someday, this will need to resolve cookbooks/other things instead of
    # just single resource targets, which is where things will get really
    # interesting, since cookbooks are going to be serieses of ExecutionThunks
    # that need to be resolved.
    thunk = (resources.lookup(target))(**kw)
    try:
        return thunk.execute().serialize()
    except Exception as err:
        return ExecutionResult.fail(err).serialize()