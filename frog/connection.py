# -*- coding: utf-8 -*-

from __future__ import annotations

import abc
import json
import logging
import shutil
from typing import List, Optional

from mitogen.core import Context
from mitogen.master import Router

from frog.util.dictser import DictSerializable

logger = logging.getLogger(__file__)


class ConnectionMethod(DictSerializable, metaclass=abc.ABCMeta):
    """ Representation of a remote connection. 
    """

    DEFAULT_PYTHON_PATH = ["/usr/bin/env", "python3"]

    @classmethod
    def load(cls, connection_method: dict) -> ConnectionMethod:
        what = connection_method.pop("type", "ssh").lower()
        method = CONNECTION_METHOD_MAP.get(what)
        if method is None:
            raise ValueError(f"Unknown connection method type: {what}")

        return method(**connection_method.pop("options", {}))

    def __init__(self, /, **kw):
        self.options = {
            "remote_name": kw.pop("remote_name", None),
            "python_path": kw.pop("python_path", self.DEFAULT_PYTHON_PATH),
            "debug": kw.pop("debug", False),
            "unidirectional": kw.pop("unidirectional", False),
            "connect_timeout": kw.pop("connect_timeout", 30),
            "profiling": kw.pop("profiling", False),
            "via": kw.pop("via", None),
        }

    @abc.abstractmethod
    def __repr__(self) -> str:
        raise NotImplemented

    @abc.abstractmethod
    def type(self) -> str:
        raise NotImplemented

    @abc.abstractmethod
    def connect(self, router: Router):
        raise NotImplemented

    def asdict(self) -> dict:
        return {
            "type": self.type(),
            "options": self.options,
        }

    def asjson(self) -> str:
        return json.dumps(self.asdict())

    def check_leftover_options(self, kw: dict):
        if len(kw) > 0:
            logger.warning(f"Options left over after constructing ConnectionMethod: {kw}")


class SshConnectionMethod(ConnectionMethod):

    TYPE = "ssh"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.options.update({
            "hostname": kw.pop("hostname"),
            "username": kw.pop("username", None),
            "ssh_path": kw.pop("ssh_path", "ssh"),
            "ssh_args": kw.pop("ssh_args", []),
            "port": kw.pop("port", None),
            "check_host_keys": kw.pop("check_host_keys", "enforce"),
            "password": kw.pop("password", None),
            "identity_file": kw.pop("identity_file", None),
            "identities_only": kw.pop("identities_only", False),
            "compression": kw.pop("compression", True),
            "ssh_debug_level": kw.pop("ssh_debug_level", 0),
        })

    def __repr__(self) -> str:
        return f"<SshConnectionMethod {self.options}>"

    def type(self) -> str:
        return self.TYPE

    def connect(self, router: Router) -> Context:
        return router.ssh(**self.options)


class DockerConnectionMethod(ConnectionMethod):

    DEFAULT_DOCKER_PATH = "docker"
    TYPE = "docker"

    def __init__(self, /, **kw):
        super().__init__(**kw)
        self.options.update({
            "container": kw.pop("container", None),
            "username": kw.pop("username", None),
            "image": kw.pop("image", None),
            "docker_path": shutil.which(kw.pop("docker_path", self.DEFAULT_DOCKER_PATH)),
        })

    def __repr__(self) -> str:
        return f"<DockerConnectionMethod {self.options}>"

    def type(self) -> str:
        return self.TYPE

    def connect(self, router: Router) -> Context:
        return router.docker(**self.options)


class PodmanConnectionMethod(DockerConnectionMethod):

    DEFAULT_PODMAN_PATH = "podman"
    TYPE = "podman"

    def __init__(self, /, **kw):
        super().__init__(**kw)
        self.options.update({
            "docker_path": shutil.which(kw.pop("podman_path", self.DEFAULT_PODMAN_PATH)),
        })

    def __repr__(self) -> str:
        return f"<PodmanConnectionMethod {self.options}>"

    def type(self) -> str:
        return self.TYPE


CONNECTION_METHOD_MAP = {
    DockerConnectionMethod.TYPE: DockerConnectionMethod,
    PodmanConnectionMethod.TYPE: PodmanConnectionMethod,
    SshConnectionMethod.TYPE: SshConnectionMethod,
}

