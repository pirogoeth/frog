# -*- coding: utf-8 -*-

from __future__ import annotations

import dataclasses
import io
import json
import pathlib
from functools import reduce
from itertools import chain
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Sized, Tuple

import yaml
from mitogen.core import Context
from mitogen.master import Router

from frog.util import yamlext
from frog.util.dictser import DictDeserializable, DictSerializable

from .connection import ConnectionMethod, SshConnectionMethod


def load(inventories: List[pathlib.Path]) -> Inventory:
    yamlext.register()

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


class Inventory(DictSerializable, Sized):
    """ Represents a collection of hosts.
    """

    hosts: Mapping[str, List[InventoryItem]]
    parent: Optional[Inventory] = None

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
        hosts = {}
        for key, items in data.get("hosts", {}).items():
            hosts.setdefault(key, [])
            for item in items:
                hosts[key].append(InventoryItem.fromdict(item))
        return cls(hosts, parent=data.get("parent"))

    @classmethod
    def fromjson(cls, data: str) -> Inventory:
        props = json.loads(data)
        return cls.fromdict(props)

    def __init__(self, hosts: Optional[Mapping[str, List[InventoryItem]]], parent: Optional[Inventory]=None):
        if hosts is None:
            hosts = {}
        self.hosts = hosts
        self.parent = parent

        for host in chain.from_iterable(self.hosts.values()):
            host.parent = self

    def __repr__(self) -> str:
        return f"<Inventory object, groups={list(self.hosts.keys())}>"

    def __iter__(self) -> Iterable[InventoryItem]:
        return chain.from_iterable(self.hosts.values())

    def __len__(self) -> int:
        return reduce(lambda acc, group: acc+len(group), self.hosts.values(), 0)

    def select(self, criteria: str) -> Inventory:
        subset: Dict[str, List[InventoryItem]] = {}

        for group, items in self.hosts.items():
            subset.setdefault(group, [])
            for item in items:
                if criteria and item.host == criteria:
                    subset[group].append(item)

        return Inventory(subset, parent=self)

    def resolve_tags(self) -> Inventory:
        """ Returns a new Inventory after calling `resolve_tags` on all InventoryItems. """

        resolved: Dict[str, List[InventoryItem]] = {}
        for group, items in self.hosts.items():
            resolved.setdefault(group, [])
            for item in items:
                resolved[group].append(item.resolve_tags())

        return Inventory(resolved, parent=self)

    def asdict(self) -> dict:
        return {
            "hosts": self.hosts,
            "parent": self.parent,
        }

    def asjson(self) -> str:
        return json.dumps(self.asdict())


class InventoryItem(DictDeserializable, DictSerializable):
    """ Represents an entry in the inventory.
    """

    """ Name of the host """
    host: str

    """ Connection method used to reach the remote. """
    _connection_method: Optional[ConnectionMethod] = None

    """ InventoryItem to use as a gateway. """
    jump_via: Optional[InventoryItem] = None

    """ Whether we should try to sudo. Default true. """
    should_sudo: bool = True

    """ Sudo options. """
    sudo_options: Optional[dict] = None

    """ Dictionary of host facts. """
    facts: Optional[dict] = None

    """ Inventory object that "owns" this InventoryItem. """
    parent: Optional[InventoryItem] = None

    @classmethod
    def fromdict(cls, data: dict) -> InventoryItem:
        return cls(**data)

    @classmethod
    def deserialize(cls, data: dict) -> InventoryItem:
        jump_via = data.pop("jump_via", None)
        if jump_via is not None:
            jump_via = InventoryItem.deserialize(jump_via)

        return cls(
            host=data.pop("host"),
            connection_method=data.pop("connection_method", {}),
            jump_via=jump_via,
            should_sudo=data.pop("should_sudo", True),
            sudo_options=data.pop("sudo_options", None),
            facts=data.pop("facts", None),
        )

    def __init__(self, host: str, connection_method: Optional[dict]=None, jump_via: Optional[InventoryItem]=None,
                 should_sudo: bool=True, sudo_options: Optional[dict]=None, facts: Optional[dict]=None):
        self.host = host
        self.jump_via = jump_via
        self.should_sudo = should_sudo
        self.sudo_options = sudo_options or {"username": "root"}
        self.facts = facts or {}
        if connection_method is None:
            connection_method = SshConnectionMethod.default(self.host)
        self.connection_method = connection_method

    def __repr__(self) -> str:
        via = ""
        if self.jump_via:
            via = f"via {self.jump_via}"

        sudo_as = ""
        if self.sudo_options:
            sudo_username = self.sudo_options.get("username")
            if sudo_username is not None:
                sudo_as = f"sudo as {sudo_username}"

        return f"<InventoryItem[{self.host}] conn={self.connection_method} {via} {sudo_as}>"

    def _get_connection_method(self) -> Optional[ConnectionMethod]:
        return self._connection_method

    def _set_connection_method(self, method: dict):
        if self._connection_method is not None:
            raise ValueError("Connection method is already set, please don't overwrite")

        self._connection_method = ConnectionMethod.load(method)

    connection_method = property(_get_connection_method, _set_connection_method)

    def asdict(self) -> dict:
        return {
            "host": self.host,
            "connection_method": self.connection_method.asdict(),
            "jump_via": self.jump_via,
            "should_sudo": self.should_sudo,
            "sudo_options": self.sudo_options,
            "facts": self.facts,
        }

    def asjson(self) -> str:
        return json.dumps(self.asdict())

    def inherits_options(self, options: dict):
        """ Performs option inheritance from the inventory file.
        """

        if not self.jump_via:
            self.jump_via = options.get("jump_via")

    def open_connection(self, router: Router) -> Context:
        ctx = self.connection_method.connect(router)
        if self.should_sudo:
            ctx = router.sudo(
                via=ctx,
                **self.sudo_options,
            )

        return ctx

    def update_facts(self, new_facts: dict):
        """ Updates the facts we have stored with a new set of facts.
            Writes the existing facts over the new set of facts, so
            facts set by hand take precedence over gathered facts.
        """

        new_facts.update({} if self.facts is None else self.facts)
        self.facts = new_facts

    def resolve_tags(self) -> InventoryItem:
        """ Returns a copy of this InventoryItem with all YAML extension tags resolved. """

        resolved = yamlext.resolve_nested_tags(self.asdict())
        return self.fromdict(resolved)