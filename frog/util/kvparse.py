# -*- coding: utf-8 -*-

import regex
from typing import Dict, List, Optional

QUOTES = "\"'"

_kvinline_pattern = regex.compile(
    r"""(?:                # Begin non capturing group for whole pair.
          (?P<key>         # Named capture for key
            [\w]+          # Capture 1+ alphanumeric values
          )                # End key capture
          =                # Literal '='
          (?P<value>       # Named capture for value
            (?:            # Begin group for escaped values
              (?P<subitem> #   Begin group for subparser groups
                {          #   Literal '{'
                  (?R)     #   Recursively match the whole thing
                }          #   Literal '}'
              )            #   End group for subparser groups
              |            # -OR-
              (?:          #  Begin group for quoted values
                '.+?'      #  Capture between two single quotes lazily.
              )            #  End capture for quoted values
              |            # -OR-
              (?:          #  Begin group for quoted values
                ".+?"      #  Capture between two double quotes lazily.
              )            #  End group for quoted values
              |            # -OR-
              (?:          #  Begin group for unquoted values
                [\S]+      #  Capture 1+ non-whitespace character
              )            #  End capture for unquoted values
            )              # End capture for possibly escaped values
          )                # End capture for value
          (?:              # Group for whitespace between pairs
            \s+            # Capture 1+ whitespace character
          )?               # End whitespace capture, optional
        )+?                # End pair capture, lazily capture 1+
""",
    regex.VERBOSE,
)


def _unpack(key: str, value: str, subitem: Optional[str] = None):
    key = key.lstrip(QUOTES).rstrip(QUOTES)
    if value == subitem:
        # Parse the subitem with the outer braces removed
        subitem = value[1:-1]
        return {key: parse(subitem)}

    return {key: value.lstrip(QUOTES).rstrip(QUOTES)}


def parse_many(items: List[str]) -> Dict[str, str]:
    """ Uses a regex to parse every item in a list.
    """

    kvitems = {}

    for item in items:
        matches = _kvinline_pattern.finditer(item)
        for match in matches:
            kvitems.update(_unpack(*match.groups()))

    return dict(kvitems.items())


def parse(data: str) -> Dict[str, str]:
    """ Uses a regex to parse data in key=value format into a
        dictionary.
    """

    kvitems = {}

    matches = _kvinline_pattern.finditer(data)
    for match in matches:
        kvitems.update(_unpack(*match.groups()))

    return dict(kvitems.items())
