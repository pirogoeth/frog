# -*- coding: utf-8 -*-

import json
from typing import List

from texttable import Texttable


def as_json(results: List[dict]) -> str:
    out = {}

    for result in results:
        out.update({result["host"].host: result["result"]})

    return json.dumps(out)


def as_texttable(results: List[dict]) -> str:
    result_rows = []
    for result in results:
        result_rows.append([result["host"].host, result["result"]])

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_header_align(["l", "r"])
    table.set_cols_align(["l", "r"])
    table.add_rows([["host", "response"], *result_rows])

    return table.draw()


def as_pretty_json(results: List[dict]) -> str:
    out = {}

    for result in results:
        out.update({result["host"].host: result["result"]})

    return json.dumps(out, indent=2)