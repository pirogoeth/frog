# -*- coding: utf-8 -*-

from itertools import zip_longest

from frog.inventory import InventoryItem


def ping(*, message: str="pong") -> str:
    """ Dumb ping on a host.
    """

    return message