# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any
from mitogen.core import Context

from frog import resources
from frog.inventory import Inventory, InventoryItem

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
    host = InventoryItem.fromdict(_host)
    inventory = Inventory.fromdict(_inventory)
    parent = _parent

    fn = resources.lookup(target)
    return fn(**kw)