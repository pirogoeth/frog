# -*- coding: utf-8 -*-

import abc
import hashlib
import io
import pathlib
import pickle
from datetime import datetime, timedelta


class FactCache(metaclass=abc.ABCMeta):

    class NeedsUpdate(Exception):
        def __init__(self, hostname: str):
            super().__init__(f"Host {hostname} needs facts updated")

    def get(self, hostname: str) -> dict:
        raise NotImplemented

    def update(self, hostname: str, data: dict) -> bool:
        raise NotImplemented


class MemoryFactCache(FactCache):

    def __init__(self):
        self._cache = {}

    def get(self, hostname: str) -> dict:
        try:
            return self._cache[hostname]
        except KeyError:
            raise FactCache.NeedsUpdate(hostname)

    def update(self, hostname: str, data: dict):
        self._cache[hostname] = data


class FilesystemFactCache(FactCache):

    def __init__(self, directory: pathlib.Path, validity_period: timedelta):
        self._dir = directory
        self._dir.mkdir(mode=0o755, exist_ok=True)
        self._validity_period = validity_period

    def __repr__(self):
        return f"<FilesystemFactCache at {self._dir} (lifetime {self._validity_period})>"

    def is_valid(self, cache_file: pathlib.Path):
        if not cache_file.exists():
            return False

        created_at = datetime.fromtimestamp(cache_file.stat().st_ctime)
        valid_until = created_at + self._validity_period
        return datetime.now() < valid_until

    def get_host_cache_path(self, hostname: str) -> pathlib.Path:
        host_hash = hashlib.md5(hostname.encode("utf-8")).hexdigest()
        return self._dir / f"{host_hash}.p"

    def get(self, hostname: str) -> dict:
        host_cache = self.get_host_cache_path(hostname)
        if not self.is_valid(host_cache):
            raise FactCache.NeedsUpdate(hostname)

        with io.open(str(host_cache.absolute()), "rb") as cache_fp:
            return pickle.load(cache_fp)

    def update(self, hostname: str, data: dict):
        host_cache = self.get_host_cache_path(hostname)
        host_cache.touch(mode=0o640)

        with io.open(str(host_cache.absolute()), "wb") as cache_fp:
            pickle.dump(data, cache_fp)