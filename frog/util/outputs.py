# -*- coding: utf-8 -*-

import json
from pprint import pformat
from typing import Any, Callable, List, Mapping

from texttable import Texttable

from frog.runner import ExecutionResult


def as_json(results: List[ExecutionResult]) -> str:
    out = {}

    for result in results:
        out.update({result.host.host: result.outcome()})

    return json.dumps(out)


def as_texttable(results: List[ExecutionResult]) -> str:
    result_rows = []
    for result in results:
        result_rows.append([result.host.host, result.outcome()])

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_header_align(["l", "r"])
    table.set_cols_align(["l", "r"])
    table.add_rows([["host", "response"], *result_rows])

    return table.draw()


def as_pretty_json(results: List[ExecutionResult]) -> str:
    out = {}

    for result in results:
        out.update({result.host.host: result.outcome()})

    return json.dumps(out, indent=2)


def as_pprint(results: List[ExecutionResult]) -> str:
    return pformat([result.asdict() for result in results])


def formatters() -> Mapping[str, Callable[[List[ExecutionResult]], str]]:
    return {
        "table": as_texttable,
        "json": as_json,
        "pretty-json": as_pretty_json,
        "pprint": as_pprint,
    }


def pick_formatter(formatter: str) -> Callable[[Any], str]:
    try:
        return formatters()[formatter.lower()]
    except KeyError:
        raise ValueError(f"Unknown formatter {formatter}")