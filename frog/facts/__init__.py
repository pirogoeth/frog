# -*- coding: utf-8 -*-

import concurrent.futures
import logging
import os

from frog import context
from frog.facts import (
    host_meta,
    network,
    platform,
)
from frog.util import Timer

logger = logging.getLogger(__name__)
_modules = [host_meta, network, platform]


def gather() -> dict:
    """ Gathers all facts for a host and returns a meta dictionary. """

    data = {}
    timer = Timer()
    with timer:
        fs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            logger.debug(f"Starting fact gathering on host {context.host.host}")
            fs = [executor.submit(mod.gather) for mod in _modules]

        for gathered in concurrent.futures.as_completed(fs):
            data.update(gathered.result())

    logger.debug(f"Done fact gathering on {context.host.host}, took {timer.time_taken}s")

    return data