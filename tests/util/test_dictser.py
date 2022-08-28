# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import List, Optional

from frog.util import dictser


class Item(dictser.DictSerializable):
    a: int
    b: str
    c: Optional[Item] = None
    d: Optional[List[Item]] = None

    def __init__(self, a: int, b: str, c: Optional[Item]=None, d: Optional[List[Item]]=None):
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def asdict(self):
        return {
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "d": self.d,
        }



def test_serialize_one():
    given = Item(1, "test")
    expected = {"a": 1, "b": "test", "c": None, "d": None}

    assert given.serialize() == expected


def test_serialize_recursive_class():
    given = Item(1, "test", c=Item(
        2, "one level deep", c=Item(
            3, "going deeper!"
        )
    ))
    expected = {
        "a": 1,
        "b": "test",
        "c": {
            "a": 2,
            "b": "one level deep",
            "c": {
                "a": 3,
                "b": "going deeper!",
                "c": None,
                "d": None,
            },
            "d": None,
        },
        "d": None,
    }

    assert given.serialize() == expected


def test_serialize_list_of_serializables():
    given = Item(1, "test", d=[
        Item(2, "a", c=Item(3, "aa")),
        Item(4, "b", c=Item(5, "bb")),
    ])
    expected = {
        "a": 1,
        "b": "test",
        "c": None,
        "d": [
            {
                "a": 2,
                "b": "a",
                "c": {
                    "a": 3,
                    "b": "aa",
                    "c": None,
                    "d": None,
                },
                "d": None,
            },
            {
                "a": 4,
                "b": "b",
                "c": {
                    "a": 5,
                    "b": "bb",
                    "c": None,
                    "d": None,
                },
                "d": None,
            },
        ],
    }

    assert given.serialize() == expected