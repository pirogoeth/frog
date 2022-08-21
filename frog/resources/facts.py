# -*- coding: utf-8 -*-

import logging

from frog import context
from frog.facts import gather as gather_host_facts

logger = logging.getLogger(__name__)


def gather() -> dict:
    """ Gathers facts from the current host. """ 

    return gather_host_facts()


def show() -> dict:
    """ Display facts for the current host. """

    return context.host.facts