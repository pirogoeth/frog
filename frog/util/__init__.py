# -*- coding: utf-8 -*-

import time

__all__ = ["deco", "dictser", "kvparse", "outputs", "packages"]


class Timer:
    """ Times the execution of a code block, returning the time taken.
        If `monotonic` is True, which is the default, uses the monotonic
        system clock for timing. Otherwise, uses the normal system time,
        which may be subject to jumps due to time syncing, leap seconds, etc.
    """

    def __init__(self):
        self._start = None
        self._time_taken = None

    def __enter__(self):
        self._start = self.measure()

    def __exit__(self, *args, **kw) -> bool:
        self._time_taken = self.measure() - self._start
        return False

    def measure(self) -> float:
        return time.perf_counter()

    @property
    def time_taken(self) -> float:
        if self._time_taken is None:
            raise Exception("Nothing has been measured!")

        return self._time_taken