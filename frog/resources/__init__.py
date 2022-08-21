# -*- coding: utf-8 -*-

import glob
import importlib
import os
import sys
from typing import Any, Callable, Dict, List
from types import ModuleType

# This line tricks mitogen into pulling all child modules over to the remote hosts.
from frog.resources import (
    facts, file, test
)

_submodules: Dict[str, ModuleType] = {
    "facts": facts,
    "file": file,
    "test": test,
}

__all__ = list(_submodules.keys())

def fqpn_leaf(fqpn: str) -> str:
    """ Returns the final element of a package path.
    """

    return fqpn.rpartition(".")[-1]


def lookup(resource: str) -> Callable:
    namespace, _, func = resource.partition(".")
    if namespace in _submodules:
        module = _submodules[namespace]
        if func != "" and func in dir(module):
            return getattr(_submodules.get(namespace), func)

    raise NameError(f"Resource named {resource} not found")