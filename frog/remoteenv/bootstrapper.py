# -*- coding: utf-8 -*-

import io
import logging
import os
import pathlib
import subprocess
import sys
import textwrap
import venv
from typing import Optional

from mitogen.core import Context, Router
from mitogen.service import FileService

from frog.util.dictser import DictDeserializable, DictSerializable, serialize_recursively

logger = logging.getLogger(__name__)


class Settings(DictDeserializable, DictSerializable):
    def __init__(
        self,
        directory: Optional[pathlib.Path]=None,
        clean: bool=False,
    ):
        if directory is None:
            directory = pathlib.Path("/opt/frog-env")

        self.directory = directory
        self.clean = clean

    def asdict(self) -> dict:
        return {
            "directory": str(self.directory),
            "clean": self.clean,
        }

    @classmethod
    def deserialize(cls, data: dict):
        return cls(
            directory=pathlib.Path(data["directory"]),
            clean=data["clean"],
        )


def bootstrap(from_ctx: Context, settings_data: Optional[dict]=None) -> str:
    """ Bootstraps a Python virtualenv that we can operate out of.
        Returns a path to the bootstrapped venv's Python.
    """

    settings = Settings.deserialize(settings_data or {})

    # So... for some reason, Mitogen(!?) modifies sys._base_executable which breaks venv.
    # Set it to sys.executable temporarily.
    _orig_base_executable = None
    if "_base_executable" in dir(sys):
        _orig_base_executable = sys._base_executable
        sys._base_executable = sys.executable

    base_dir = pathlib.Path(settings.directory)
    venv.create(
        str(base_dir),
        system_site_packages=False,
        clear=False,
        with_pip=True,
    )

    # Restore _base_executable
    if _orig_base_executable is not None:
        sys._base_executable = _orig_base_executable

    # Fetch the requirements.txt into the remote environment
    requirements_path = str(base_dir / "requirements.txt")
    with io.BytesIO() as buffer:
        success, _ = FileService.get(
            from_ctx,
            "frog/remoteenv/requirements.txt",
            buffer,
        )
        if not success:
            raise RuntimeError(f"Bootstrapping failed on {from_ctx}")

        buffer.seek(0)
        with io.open(requirements_path, "wb") as requirements_file:
            w = requirements_file.write(buffer.read())
            logger.debug(f"wrote {w} bytes to {requirements_path}")

    pip = str(base_dir / "bin" / "pip3")
    try:
        result = subprocess.check_output(
            [pip, "install", "-r", str(requirements_path)],
        )

        logger.debug(f"pip3 venv bootstrapping result: {result}")

        return str(base_dir / "bin" / "python3")
    except subprocess.CalledProcessError as err:
        logger.exception(f"""Remote dependency installation failed
stdout:
{textwrap.indent((err.stdout or b"<empty>").decode("utf-8"), "    ")}

stderr:
{textwrap.indent((err.stderr or b"<empty>").decode("utf-8"), "    ")}""")
        raise