# -*- coding: utf-8 -*-

from frog.util.deco import recipe


def package_root() -> str:
    return __path__[0]