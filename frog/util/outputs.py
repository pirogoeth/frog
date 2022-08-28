# -*- coding: utf-8 -*-

import json
from typing import List

from texttable import Texttable

from frog.runner import ExecutionResult


def as_json(results: List[ExecutionResult]) -> str:
    out = {}

    for result in results:
        out.update({result.host: result.outcome()})

    return json.dumps(out)


def as_texttable(results: List[ExecutionResult]) -> str:
    result_rows = []
    for result in results:
        result_rows.append([result.host, result.outcome()])

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_header_align(["l", "r"])
    table.set_cols_align(["l", "r"])
    table.add_rows([["host", "response"], *result_rows])

    return table.draw()


def as_pretty_json(results: List[ExecutionResult]) -> str:
    out = {}

    for result in results:
        out.update({result.host: result.outcome()})

    return json.dumps(out, indent=2)