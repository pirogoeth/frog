# -*- coding: utf-8 -*-

import logging
import os
import pathlib
import sys
from itertools import chain, zip_longest
from typing import Any, Callable, List

import click
from texttable import Texttable

from . import (
    inventory, 
    resources,
    remoteenv,
    runner,
)
from .fact_cache import FilesystemFactCache, MemoryFactCache
from .util import kvparse, outputs

logger = logging.getLogger(__name__)

DEFAULT_BOOTSTRAP_DIRECTORY = "/opt/frog-env"
DEFAULT_BOOTSTRAP_CLEAN = False
DEFAULT_MITOGEN_DEBUG = False


@click.group()
@click.option("-i", "--inventories", type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True), multiple=True, help="Path(s) to inventories to include")
@click.option("--log-level", type=str, default="INFO", help="Log level, defaults to INFO")
@click.option("--mitogen-debug/--no-mitogen-debug", type=bool, default=DEFAULT_MITOGEN_DEBUG, help="Should Mitogen debugging be turned on")
@click.pass_context
def root(ctx: click.Context, inventories: List[str], log_level: str, mitogen_debug: bool):
    """ Home-grown infrastructure management tool built with Fabric.
    """
    ctx.ensure_object(dict)

    log_level = logging._nameToLevel[log_level]

    logging.basicConfig(level=log_level, stream=sys.stdout, format="[%(levelname)s] [%(asctime)s] %(message)s")
    if not mitogen_debug:
        logging.getLogger("mitogen").setLevel(logging.INFO)

    logger.debug(f"Load inventory from {inventories}")

    inv_paths = [pathlib.Path(i) for i in inventories]
    ctx.obj["inventory"] = inventory.load(inv_paths)


@root.group("inventory")
def _inventory():
    """ Manage host inventory
    """
    pass


@_inventory.command("show")
@click.pass_context
def _inventory_show(ctx: click.Context):
    """ Load and display the inventory.
    """
    inv = ctx.obj["inventory"]

    group_rows: List[List[str]] = []
    for group, hosts in inv.hosts.items():
        group_rows.extend(zip_longest([group], [h.host for h in hosts], fillvalue=""))

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_header_align(["l", "r"])
    table.set_cols_align(["l", "r"])
    table.add_rows([["group", "host"], *group_rows])
    print(table.draw())


@_inventory.command("list")
@click.pass_context
def _inventory_list(ctx: click.Context):
    """ Load and list the inventory.
    """
    inv = ctx.obj["inventory"]

    for host in chain.from_iterable(inv.hosts.values()):
        print(f"{host.host}")


@root.command("run")
@click.option("-c", "--cookbooks", type=click.Path(exists=True, dir_okay=True, file_okay=False), help="Path to directory containing cookbooks", multiple=True)
@click.option("-l", "--limit", help="Limit hosts that should be pinged")
@click.option("-o", "--outputter", help="Output formatter function", type=click.Choice(["table", "json", "pretty-json"]), default="json")
@click.option("--bootstrap-directory", help="Directory the tool should be bootstrapped into", type=str, default=DEFAULT_BOOTSTRAP_DIRECTORY)
@click.option("--bootstrap-clean", help="Whether bootstrap directory should be cleaned before bootstrapping", type=bool, default=DEFAULT_BOOTSTRAP_CLEAN)
@click.option("--fact-cache-type", help="Type of fact cache to use", type=click.Choice(["memory", "filesystem"], case_sensitive=False), default="memory")
@click.option("--fact-cache-dir", help="Where the facts cache should be stored", type=click.Path(exists=False, dir_okay=True, file_okay=False, writable=True, readable=True, resolve_path=True, path_type=pathlib.Path), default="/tmp/infra-facts-cache")
@click.option("--fact-cache-lifetime", help="How long the facts cache should be considered valid", type=click.INT, default=3600)
@click.argument("target")
@click.argument("parameters", nargs=-1)
@click.pass_context
def _run(ctx: click.Context, cookbooks: List[str], limit: str, outputter: str,
         bootstrap_directory: str, bootstrap_clean: bool, fact_cache_type: str, fact_cache_dir: pathlib.Path,
         fact_cache_lifetime: int, target: str, parameters: List[str]):
    """ Run the cookbook or resource on the host(s) specified.
    """

    _runner = runner.Runner()

    bootstrap_settings = remoteenv.Settings(directory=bootstrap_directory, clean=bootstrap_clean)
    if fact_cache_type.lower() == "memory":
        fact_cache = MemoryFactCache()
    elif fact_cache_type.lower() == "filesystem":
        fact_cache = FilesystemFactCache(fact_cache_dir, fact_cache_lifetime)

    cookbook_paths = []
    for path in cookbooks:
        cookbook_paths.append(os.path.realpath(path))

    formatter = pick_formatter(outputter)
    resource_params = kvparse.parse_many(parameters)

    inv = ctx.obj["inventory"]

    _runner.gather_facts(inv, fact_cache=fact_cache)
    if limit:
        inv = inv.select(limit)
    results = list(_runner.execute(inv, target, resource_params))
    _runner.close()

    print(formatter(results))


def pick_formatter(formatter: str) -> Callable[[Any], str]:
    try:
        return {
            "table": outputs.as_texttable,
            "json": outputs.as_json,
            "pretty-json": outputs.as_pretty_json,
        }[formatter.lower()]
    except KeyError:
        raise ValueError(f"Unknown formatter {formatter}")