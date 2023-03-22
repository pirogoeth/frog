# -*- coding: utf-8 -*-

import logging

from frog import context
from frog.facts import gather as gather_host_facts
from frog.execution import ExecutionResult, thunk

logger = logging.getLogger(__name__)


@thunk
def gather() -> ExecutionResult:
    """ Gathers facts from the current host. """ 

    return gather_host_facts()


@thunk
def show() -> ExecutionResult:
    """ Display facts for the current host. """

    return context.host.facts