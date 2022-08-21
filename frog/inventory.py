# -*- coding: utf-8 -*-

from __future__ import annotations

import dataclasses
import io
import json
import pathlib
from itertools import chain
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml


def load(inventories: List[pathlib.Path]) -> Inventory:
    loaded = []
    while len(inventories) > 0:
        inv_path = inventories.pop(0)
        if inv_path.is_dir():
            for subpath in inv_path.iterdir():
                if subpath.is_dir():
                    inventories.append(subpath)
                else:
                    loaded.append(_load_file(subpath))
        else:
            loaded.append(_load_file(inv_path))

    return Inventory.combine(loaded)


def _load_file(inv_path: pathlib.Path) -> Tuple[str, dict]:
    with io.open(inv_path, "r") as inv_file:
        inv_name = inv_path.stem
        return (inv_name, yaml.safe_load(inv_file))


@dataclasses.dataclass
class Inventory:
    """ Represents a collection of hosts.
    """

    hosts: Mapping[str, List[InventoryItem]] = dataclasses.field(default_factory=dict)
    parent: Optional[Inventory] = dataclasses.field(default=None)

    @classmethod
    def combine(cls, inventories: List[Tuple[str, dict]]) -> Inventory:
        hosts: Dict[str, List[InventoryItem]] = {}
        for (group, inventory) in inventories:
            options = inventory.get("options", {})
            hosts.setdefault(group, [])
            items = [InventoryItem(**host) for host in inventory.get("hosts", [])]
            [item.inherits_options(options) for item in items]
            hosts[group].extend(items)

        return Inventory(hosts)

    @classmethod
    def fromdict(cls, data: dict) -> Inventory:
        return cls(**data)

    @classmethod
    def fromjson(cls, data: str) -> Inventory:
        props = json.loads(data)
        return cls.fromdict(props)

    def __repr__(self) -> str:
        return f"<Inventory object, groups={list(self.hosts.keys())}>"

    def __iter__(self) -> Iterable[InventoryItem]:
        return chain.from_iterable(self.hosts.values())

    def select(self, criteria: str) -> Inventory:
        subset: Dict[str, List[InventoryItem]] = {}

        for group, items in self.hosts.items():
            subset.setdefault(group, [])
            for item in items:
                if criteria and item.host == criteria:
                    subset[group].append(item)

        return Inventory(subset, parent=self)

    def asdict(self) -> dict:
        return dataclasses.asdict(self)

    def asjson(self) -> str:
        return json.dumps(self.asdict)


@dataclasses.dataclass
class InventoryItem:
    """ Represents an entry in the inventory.
    """

    """ Hostname to connect to. """
    host: str

    """ Port to connect on. """
    port: int = 22

    """ Name of the host to use as a gateway. """
    jump_via: Optional[str] = None

    """ User to sudo as. """
    sudo_as: Optional[str] = "root"

    """ Dictionary of host facts. """
    facts: dict = dataclasses.field(default_factory=dict)

    @classmethod
    def fromdict(cls, data: dict) -> InventoryItem:
        return cls(**data)

    def __repr__(self) -> str:
        via = ""
        if self.jump_via:
            via = f"via {self.jump_via}"

        sudo_as = ""
        if self.sudo_as:
            sudo_as = f"as {self.sudo_as}"

        return f"<InventoryItem@{hex(id(self))} {self.host}:{self.port} {via} {sudo_as}>"

    def asdict(self) -> dict:
        return dataclasses.asdict(self)

    def asjson(self) -> str:
        return json.dumps(self.asdict)

    def inherits_options(self, options: dict):
        """ Performs option inheritance from the inventory file.
        """

        if not self.jump_via:
            self.jump_via = options.get("jump_via")

    def update_facts(self, new_facts: dict):
        """ Updates the facts we have stored with a new set of facts.
            Writes the existing facts over the new set of facts, so
            facts set by hand take precedence over gathered facts.
        """

        new_facts.update(self.facts)
        self.facts = new_facts