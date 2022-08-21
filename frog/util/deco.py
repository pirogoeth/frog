# -*- coding: utf-8 -*-

import functools
import inspect
import logging
import typing
from typing import Callable, List, Type

logger = logging.getLogger(__name__)


def get_parameter_name_by_type(fn: Callable, param_type: Type) -> str:
    """ Return the name of a function's parameter that accepts a
        specific type
    """

    name = {v: k for k, v in typing.get_type_hints(fn).items()}.get(param_type)
    if name is None:
        raise NameError(f"could not find named function parameter to accept `{param_type}`")

    return name


def hydrate_from_dict(target_type: Type) -> Callable:
    """ This decorator matches a parameter's type to the parameter name,
        extracts the argument value from the call, and uses it to populate
        a `target_type`, and then passes that `target_type` to the function,
        in place of the dict version of the argument.
    """

    def _hydrate_outer(fn: Callable) -> Callable:
        # Pre-construct a signature of the function to enclose into _inner.
        # The function shouldn't change after first load, right? RIGHT?
        signature = inspect.signature(fn)
        target_parameter_name = get_parameter_name_by_type(fn, target_type)

        @functools.wraps(fn)
        def _hydrate_inner(*args, **kw):
            bound = signature.bind(*args, **kw)
            load_from = bound.arguments[target_parameter_name]
            bound.arguments[target_parameter_name] = target_type.__new__(**load_from)

            return fn(*bound.args, **bound.kwargs)

        return _hydrate_inner

    return _hydrate_outer


def recipe(desc: str, depends_on: List[Callable]):
    """ Marks a function as a recipe to be run and assists in
        the creation of a dependency graph.
    """

    def _inner(fn: Callable) -> Callable:
        logger.warning("@recipe is not actually implemented, fyi")
        return fn

    return _inner