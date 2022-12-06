# -*- coding: utf-8 -*-

import abc
import builtins
import copy
import inspect
import types
from typing import Any, Collection, Container, Dict, Generic, Iterable, List, Optional, TypeVar

DT = TypeVar("DT")


def value_type_is_builtin(value: Any) -> bool:
    if value is None:
        return True

    _type = type(value)
    _type_name = _type.__name__
    _in_builtins = _type_name in dir(builtins)
    if _in_builtins:
        _matches_builtin = getattr(builtins, _type_name) is _type
        return _in_builtins and _matches_builtin

    _in_types = _type_name in dir(types)
    if _in_types:
        _matches_type = getattr(types, _type_name) is _type
        return _in_types and _matches_type

    return False


def update_item_in(ct: Collection, idx: int, item: str, new_value: Any):
    """ Updates a slot inside of a Collection. Supports dicts, lists, sets.
    """

    if isinstance(ct, dict):
        ct[item] = new_value
    elif isinstance(ct, list):
        ct[idx] = new_value
    elif isinstance(ct, set):
        ct.remove(idx)
        ct.add(new_value)
    else:
        raise TypeError(f"Unsupported type {type(ct)}")


class DictSerializable(metaclass=abc.ABCMeta):
    """ Defines an interface for classes that are serializable to simple dictionaries,
        suitable for being sent over the wire (via Mitogen's control channels).
    """

    @abc.abstractmethod
    def asdict(self):
        """ Returns a representation of this class as a dictionary.
        """

        raise NotImplemented

    def serialize(self, deepcopy: bool=False) -> dict:
        """ Serializes this class and all members into a dict, recursively converting
            compatible member properties to built-in types where possible. 
            Raises TypeError if a member is not serializable.
        """

        # We have the benefit of not having to scan all attributes to know what we care about -
        # use the accompanying as_dict implementation to figure out which properties
        # should be serialized as well and drill in.
        this_dict = self.asdict()
        if deepcopy:
            this_dict = copy.deepcopy(this_dict)

        for member in this_dict.keys():
            this_dict[member] = serialize_recursively(this_dict[member], path_hints=[member])

        return this_dict


def serialize_recursively(item: Any, path_hints: Optional[List[str]]=None) -> Any:
    if path_hints is None:
        path_hints = []

    if isinstance(item, DictSerializable):
        return item.serialize()
    elif isinstance(item, list):
        for idx, value in enumerate(item):
            if value_type_is_builtin(value) or isinstance(value, DictSerializable):
                item[idx] = serialize_recursively(value, path_hints=path_hints + [str(idx)])
            else:
                raise TypeError(f"Type {type(value)} unserializable at {'.'.join(path_hints)}")
    elif isinstance(item, set):
        for value in item:
            if value_type_is_builtin(value) or isinstance(value, DictSerializable):
                item.remove(value)
                item.add(serialize_recursively(value, path_hints=path_hints))
            else:
                raise TypeError(f"Type {type(value)} (value {value}) unserializable at {'.'.join(path_hints)}")
    elif isinstance(item, dict):
        for key, value in item.items():
            if value_type_is_builtin(value) or isinstance(value, DictSerializable):
                item[key] = serialize_recursively(value, path_hints=path_hints + [key])
            else:
                raise TypeError(f"Type {type(value)} unserializable at {'.'.join(path_hints + [key])}")
    elif value_type_is_builtin(item):
        return item
    else:
        raise TypeError(f"Type {type(item)} unserializable at {'.'.join(path_hints)}")

    return item


class DictDeserializable(Generic[DT], metaclass=abc.ABCMeta):
    """ Chaotic counterpart to DictSerializable.
        Any object that expects to travel back and forth over the wire
        should implement this class. 

        The implementer _must_ have knowledge of the type a member is
        expected to be when deserialization occurs. If the member is
        a non-string, non-DictDeserializable type, the implementer is
        expected to handle the coercion of the member from string into
        the proper type.

        Real fancy way of saying, "fucken do it yerself", eh?
    """

    @abc.abstractclassmethod
    def deserialize(cls, data: dict) -> DT:
        """ deserialize should take all relevant items out of `data`
            and set them on a new instance of `cls`.

            It is up to the deserializer's implementation to throw
            if any unsupported or extra items are provided.
        """

        raise NotImplemented