# -*- coding: utf-8 -*-

import json
from functools import partial
from pprint import pformat
from typing import Any, Callable, List, Mapping, Union

from texttable import Texttable

from frog.execution import ExecutionResult, ResultChain
from frog.util.dictser import DictSerEncoder

ResultType = Union[ExecutionResult, ResultChain]

_json_dumps = partial(json.dumps, cls=DictSerEncoder)


def as_json(results: List[ResultType]) -> str:
    out = {}

    for result in results:
        out.update({result.host.host: result.outcome_list()})

    return _json_dumps(out)


def as_texttable(results: List[ResultType]) -> str:
    result_rows = []
    for result in results:
        result_rows.append([result.host.host, result.outcome_list()])

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_header_align(["l", "r"])
    table.set_cols_align(["l", "r"])
    table.add_rows([["host", "response"], *result_rows])

    return table.draw()


def as_pretty_json(results: List[ResultType]) -> str:
    out = {}

    for result in results:
        out.update({result.host.host: result.outcome_list()})

    return _json_dumps(out, indent=2)


def as_pprint(results: List[ResultType]) -> str:
    return pformat([result.asdict() for result in results])


def formatters() -> Mapping[str, Callable[[List[ResultType]], str]]:
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