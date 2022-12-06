# -*- coding: utf-8 -*-

from __future__ import annotations

import abc
import logging
import os
import yaml
from typing import Any, Generic, Optional, TypeVar

from prompt_toolkit import prompt

logger = logging.getLogger(__name__)

T = TypeVar("T")

U_PADLOCK = "🔒"
_EMPTY = object()


def resolve_nested_tags(obj: Any) -> Any:
    if isinstance(obj, (int, float, str, type(None))):
        return obj
    elif isinstance(obj, dict):
        updated = {}
        for key, value in obj.items():
            if isinstance(value, TagBase):
                updated[key] = value.get_value()
            else:
                updated[key] = resolve_nested_tags(value)
        obj.update(updated)
    elif isinstance(obj, (list, set)):
        for idx in range(len(obj)):
            item = obj[idx]
            if isinstance(item, TagBase):
                obj[idx] = item.get_value()
            else:
                obj[idx] = resolve_nested_tags(item)
    elif isinstance(obj, tuple):
        replacement = []
        for item in obj:
            if isinstance(item, TagBase):
                replacement.append(item.get_value())
            else:
                replacement.append(resolve_nested_tags(item))
    else:
        logger.warning(f"Unhandled type in resolve_nested_tags: {type(obj)} value {obj}")

    return obj


class TagBase(Generic[T], metaclass=abc.ABCMeta):
    yaml_tag = "!CHANGEME"

    @classmethod
    def register(cls):
        yaml.SafeLoader.add_constructor(cls.yaml_tag, cls.from_yaml)
        yaml.SafeDumper.add_multi_representer(cls, cls.to_yaml)

    @classmethod
    def from_yaml(cls, loader: yaml.Loader, node: yaml.Node) -> TagBase:
        if isinstance(node, yaml.ScalarNode):
            return cls(node.value)
        elif isinstance(node, yaml.SequenceNode):
            data = loader.construct_sequence(node, deep=True)
            if len(data) == 1:
                arg = node.value[0].value
                logger.info(
                    "Single-argument tag declaractions can be bare strings, "
                    f"and do not need to be in a sequence - try `{cls.yaml_tag} '{arg}'`")
                return cls(arg)
            else:
                args, kw = data
                return cls(args, **kw)

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, tag: TagBase) -> yaml.Node:
        return dumper.represent_yaml_object(cls.yaml_tag, tag.get_tag_data())

    @abc.abstractmethod
    def get_tag_data(self) -> str:
        raise NotImplemented

    @abc.abstractmethod
    def get_value(self) -> T:
        raise NotImplemented


class EnvironmentTag(TagBase[str]):
    yaml_tag = "!env"

    def __init__(self, env_var_name: str):
        self.env_var_name = env_var_name

    def __repr__(self) -> str:
        v = self.get_value()
        return f"<EnvironmentTag({self.env_var_name}={v})>"

    def get_tag_data(self) -> str:
        return self.env_var_name

    def get_value(self) -> str:
        return os.environ.get(self.env_var_name) or ""


class PromptTag(TagBase[str]):
    yaml_tag = "!prompt"

    def __init__(self, prompt_text: str, **kw):
        self.prompt_text = prompt_text
        self.masked = kw.get("masked", False)

    def __repr__(self) -> str:
        return f"<PromptTag({self.prompt_text=}, {self.masked=})>"

    def get_tag_data(self) -> str:
        return self.prompt_text

    def get_value(self) -> str:
        prompt_text = f"{self.prompt_text} "
        if self.masked:
            prompt_text = f"{U_PADLOCK} {prompt_text}(masked) "

        return prompt(prompt_text, is_password=self.masked)


class EnvironmentOrPromptTag(TagBase[str]):
    yaml_tag = "!env_or_prompt"

    def __init__(self, env_var_name: str, prompt: Optional[str]=_EMPTY, masked: Optional[bool]=_EMPTY):
        """ Here's the jive - this tag _CAN_ accept more complex data. As in, a series of items
            to configure its behavior. In complex cases, it's a list of `yaml.Node`. In the simplest of cases,
            it's a simple string.
        """

        self.env_var_name = env_var_name

        if masked is _EMPTY:
            basis = self.env_var_name.lower()
            triggers = ["secret", "password", "pass", "key", "masked"]
            # Assume this should masked for safety based on a trigger word
            self.masked = any(trigger in basis for trigger in triggers)
        else:
            self.masked = masked

        if prompt is _EMPTY:
            self.prompt_text = f"Value for {self.env_var_name}? "
        else:
            self.prompt_text = prompt

    def __repr__(self) -> str:
        return f"<EnvironmentOrPromptTag({self.env_var_name=}, {self.prompt_text=}, {self.masked=})>"

    def get_tag_data(self) -> str:
        return [self.env_var_name, self.options]

    def get_value(self) -> str:
        value = os.environ.get(self.env_var_name, _EMPTY)
        if value is _EMPTY:
            prompt_text = f"{self.prompt_text} "
            if self.masked:
                prompt_text = f"{U_PADLOCK} {prompt_text}(masked) "

            return prompt(prompt_text, is_password=self.masked)


def register():
    classes = [EnvironmentTag, PromptTag, EnvironmentOrPromptTag]

    for cls in classes:
        logger.debug(f"Registering YAML object: {cls}")
        try:
            cls.register()
        except Exception:
            logger.exception("YAML object failed to register")