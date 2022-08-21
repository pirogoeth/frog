# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import logging
import re
import socket

_hostname_regex = re.compile(r"""
    ^                               # beginning of string
        (?P<app>[a-z_-]+)           # matches the app name
        -                           # separator between app name and node num
        n(?P<node>\d{2,})           # match node num w/o leading `n`
        \.                          # next domain part
        (?P<datacenter>             # capture region + datacenter num
            (?P<region>[a-z]{3})    # nested capture region only
        \d?)                        # capture optional datacenter num
        \.                          # next domain part
        (?P<domain>.+)              # capture remaining chunk of domain
    $                               # end of string
""", re.VERBOSE)
logger = logging.getLogger(__name__)


def _data_from_name(hostname: str):
    """ Parses out name to variables
    """

    rematch = _hostname_regex.search(hostname)
    if rematch is None:
        logger.debug(f"Hostname is not in expected format, can't gather")
        return {}

    return {
        "app": rematch.group("app"),
        "node": rematch.group("node"),
        "datacenter": rematch.group("datacenter"),
        "region": rematch.group("region"),
        "parent_domain": rematch.group("domain"),
    }


def gather() -> dict:
    hostname = socket.gethostname()
    facts = dict(fqdn=hostname, **_data_from_name(hostname))
    logger.debug(f"Gathered {len(facts)} facts")
    return facts