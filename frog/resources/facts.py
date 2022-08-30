# -*- coding: utf-8 -*-

import logging

from frog import context
from frog.facts import gather as gather_host_facts
from frog.result import ExecutionResult

logger = logging.getLogger(__name__)


def gather() -> ExecutionResult:
    """ Gathers facts from the current host. """ 

    return ExecutionResult.ok(facts=gather_host_facts())


def show() -> ExecutionResult:
    """ Display facts for the current host. """

    return ExecutionResult.ok(facts=context.host.facts)