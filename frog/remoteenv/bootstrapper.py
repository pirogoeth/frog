# -*- coding: utf-8 -*-

import io
import logging
import pathlib
import subprocess
import textwrap
import venv
from typing import Optional

from mitogen.core import Context, Router
from mitogen.service import FileService

logger = logging.getLogger(__name__)


class Settings:
    def __init__(
        self,
        directory: str="/opt/infra-env",
        clean: bool=False,
    ):
        self.directory = directory
        self.clean = clean


def bootstrap(from_ctx: Context, settings: Optional[Settings]=None) -> str:
    """ Bootstraps a Python virtualenv that we can operate out of.
        Returns a path to the bootstrapped venv's Python.
    """
    if settings is None:
        settings = Settings()

    base_dir = pathlib.Path(settings.directory)
    venv.create(
        base_dir,
        system_site_packages=False,
        clear=False,
        with_pip=True,
    )

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