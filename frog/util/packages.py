# -*- coding: utf-8 -*-

import glob
import importlib
import os
from pathlib import Path
from types import ModuleType
from typing import Iterable, Iterator


def get_package_directory(module_path: str) -> Path:
    return Path(os.path.dirname(module_path))


def find_sibling_modules(module_path: str) -> Iterable[str]:
    return glob.glob(os.path.dirname(module_path) + "/*.py")


def get_sibling_modules(module_path: str) -> Iterable[str]:
    modules = find_sibling_modules(module_path)
    return [
        os.path.basename(f)[:-3] for f in modules
        if not os.path.basename(f).startswith('_') and
        not f.endswith('__init__.py') and os.path.isfile(f)
    ]


def load_sibling_modules(package: str, module_path: str) -> Iterator[ModuleType]:
    for module in get_sibling_modules(module_path):
        yield importlib.import_module(f"{package}.{module}")