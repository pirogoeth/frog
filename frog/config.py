# -*- coding: utf-8 -*-

from __future__ import annotations

import configparser
import io
import pathlib
from datetime import timedelta
from typing import Any

DEFAULT_BOOTSTRAP_DIRECTORY = "/opt/frog-env"
DEFAULT_BOOTSTRAP_CLEAN = False
DEFAULT_FACT_CACHE_TYPE = "memory"
DEFAULT_MITOGEN_DEBUG = False
DEFAULT_LOG_FORMAT = "[%(levelname)s] [%(asctime)s] %(message)s"
DEFAULT_LOG_LEVEL = "INFO"


class Config:

    CONVERTERS = {
        "path": pathlib.Path,
        "seconds": lambda seconds: timedelta(seconds=int(seconds)),
    }

    @classmethod
    def load(cls, from_path: pathlib.Path) -> Config:
        parser = configparser.ConfigParser(converters=cls.CONVERTERS)
        defaults = {
            "bootstrap": {
                "directory": DEFAULT_BOOTSTRAP_DIRECTORY,
                "clean": DEFAULT_BOOTSTRAP_CLEAN,
            },
            "mitogen": {
                "default": DEFAULT_MITOGEN_DEBUG,
            },
            "logging": {
                "log level": DEFAULT_LOG_LEVEL,
                "format": DEFAULT_LOG_FORMAT,
            },
            "fact cache": {
                "type": DEFAULT_FACT_CACHE_TYPE,
            }
        }
        parser.read_dict(defaults)
        with io.open(str(from_path), "r") as cfg_file:
            parser.read_file(cfg_file)

        return cls(parser)

    def __init__(self, parser: configparser.ConfigParser):
        self._parser = parser

    def get(self, *args, **kw) -> Any:
        return self._parser.get(*args, **kw)

    def getint(self, *args, **kw) -> Any:
        return self._parser.getint(*args, **kw)

    def getfloat(self, *args, **kw) -> Any:
        return self._parser.getfloat(*args, **kw)

    def getbool(self, *args, **kw) -> Any:
        return self._parser.getboolean(*args, **kw)

    def getpath(self, *args, **kw) -> Any:
        return self._parser.getpath(*args, **kw)

    def getseconds(self, *args, **kw) -> Any:
        return self._parser.getseconds(*args, **kw)