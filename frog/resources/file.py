# -*- coding: utf-8 -*-

import grp
import io
import logging
import os
import pwd
from re import I
from typing import Optional, Union

from mitogen.service import FileService

from frog.inventory import InventoryItem
from frog.execution import ExecutionResult, thunk

logger = logging.getLogger(__name__)


@thunk
def exists(*, path: str) -> bool:
    """ Returns a boolean of whether a file/directory exists on disk.
    """

    return os.path.exists(path)


@thunk
def file_exists(*, path: str) -> bool:
    """ Returns whether a file exists on disk and is a file.
    """

    return os.path.isfile(path)


@thunk
def dir_exists(*, path: str) -> bool:
    """ Returns whether a directory exists on disk and is a directory.
    """

    return os.path.isdir(path)


@thunk
def stat(*, path: str, follow_symlinks: bool=False) -> dict:
    """ Returns a stat structure for a file or directory.
    """

    stat_result = os.stat(path, follow_symlinks=follow_symlinks)
    fields = [f for f in dir(stat_result) if f.startswith("st")]
    values = [getattr(stat_result, f) for f in fields]

    return dict(zip(fields, values))


@thunk
def mkdirs(*, path: str, create_mode: int=0o750, exist_ok: bool=False):
    """ Makes a directory and all parent directories leading to it.
    """

    return os.makedirs(path, mode=create_mode, exist_ok=exist_ok)


@thunk
def touch(*, path: str, create_mode: int=0o640, exist_ok: bool=True, update_create_time: Optional[int]=None):
    """ Creates a file at the specified path.
    """

    fmode = "x" if not exist_ok else "a"
    with io.open(path, fmode) as f:
        f.write("")

    _update_file_mode(path=path, mode=create_mode)

    if update_create_time:
        fstat = os.stat(path)
        os.utime(path, times=(fstat.st_atime, update_create_time))


def _update_file_mode(*, path: str, mode: int) -> bool:
    """ Returns true if the file mode was updated.
    """

    fstat = os.stat(path, follow_symlinks=True)
    if (fstat.st_mode & 0o777) != mode:
        os.chmod(path, mode=mode, follow_symlinks=True)
        return True

    return False


def _update_file_ownership(*, path: str, owner: Union[int, str], group: Union[int, str], follow_symlinks: bool=False) -> bool:
    """ Returns true if the file ownership was updated.
    """

    if isinstance(owner, int):
        to_uid = owner
    else:
        to_uid = pwd.getpwnam(owner).pw_uid

    if isinstance(group, int):
        to_gid = group
    else:
        to_gid = grp.getgrnam(group).gr_gid

    fstat = os.stat(path, follow_symlinks=True)
    if fstat.st_uid != to_uid or fstat.st_gid != to_gid:
        os.chown(path, to_uid, to_gid, follow_symlinks=follow_symlinks)
        return True

    return False


@thunk
def get_contents(*, path: str):
    """ Returns the contents of the file at `path`.
    """

    with io.open(path, "r") as f:
        return f.read()


@thunk
def put(*, path: str, contents: str, mode: int=0o600, owner: Optional[str]=None, group: Optional[str]=None, overwrite: bool=False, encoding: Optional[str]=None):
    """ Places contents onto the remote at path.
    """

    if encoding is None:
        encoding = "utf-8"

    contents = contents.encode(encoding)

    logger.debug(f"Writing {len(contents)} bytes to path {path}")

    fmode = "wb" if overwrite else "xb"
    with io.open(path, fmode) as f:
        if overwrite:
            f.truncate(0)
        f.write(contents)

    # if owner or group are not set, inherit from the user we're running as
    if owner is None:
        owner = os.geteuid()
        logger.debug(f"No owner set, defaulting to {owner} (for {path})")

    if group is None:
        group = os.getegid()
        logger.debug(f"No group set, defaulting to {group} (for {path})")

    updated = []
    updated.append(_update_file_mode(path=path, mode=mode))
    updated.append(_update_file_ownership(path=path, owner=owner, group=group))

    return any(updated)