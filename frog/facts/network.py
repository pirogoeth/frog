# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import subprocess
from typing import Iterable, List, Optional

import netifaces

logger = logging.getLogger(__name__)


def gather() -> dict:
    network = {}

    interfaces = netifaces.interfaces()
    network["interface"] = {}
    network["interfaces"] = interfaces
    for iface in interfaces:
        network["interface"].setdefault(iface, {})
        network["interface"][iface].setdefault("ipv4", [])
        network["interface"][iface].setdefault("ipv6", [])
        for afnum, addresses in netifaces.ifaddresses(iface).items():
            fam = {netifaces.AF_INET: "ipv4", netifaces.AF_INET6: "ipv6"}.get(afnum)
            if fam is None:
                continue

            for address in addresses:
                network["interface"][iface][fam].append(address)


    logger.debug(f"Gathered {len(network)} facts")
    return {"network": network}
