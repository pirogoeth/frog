# -*- coding: utf-8 -*-

import logging
import os
import pathlib
import sys
from itertools import chain, zip_longest
from typing import Any, Callable, List

import better_exceptions  # noqa: F401
import click
from texttable import Texttable

from . import (
    config,
    inventory, 
    resources,
    remoteenv,
    runner,
)
from .fact_cache import FilesystemFactCache, MemoryFactCache
from .util import kvparse, outputs

logger = logging.getLogger(__name__)


@click.group()
@click.option("-c", "--config-path", type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True), help="Path to a configuration file")
@click.option("-i", "--inventories", type=click.Path(exists=True, dir_okay=True, readable=True, resolve_path=True), multiple=True, help="Path(s) to inventories to include")
@click.option("--log-level", type=str, default=None, help="Log level, defaults to INFO")
@click.option("--mitogen-debug/--no-mitogen-debug", type=bool, default=None, help="Should Mitogen debugging be turned on")
@click.pass_context
def root(ctx: click.Context, config_path: pathlib.Path, inventories: List[str], log_level: str, mitogen_debug: bool):
    """ Home-grown infrastructure management tool built with Fabric.
    """
    ctx.ensure_object(dict)

    cfg = config.Config.load(config_path)

    log_level = log_level or cfg.get("logging", "log level")
    log_format = cfg.get("logging", "format", raw=True)
    logging.basicConfig(level=logging._nameToLevel[log_level], stream=sys.stdout, format=log_format)
    if not any([mitogen_debug, cfg.getbool("mitogen", "debug")]):
        logging.getLogger("mitogen").setLevel(logging.INFO)

    logger.debug(f"Load inventory from {inventories}")

    inv_paths = [pathlib.Path(i) for i in inventories]
    ctx.obj["config"] = cfg
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
@click.option("-o", "--outputter", help="Output formatter function", type=click.Choice(outputs.formatters().keys()), default="json")
@click.argument("target")
@click.argument("parameters", nargs=-1)
@click.pass_context
def _run(ctx: click.Context, cookbooks: List[str], limit: str, outputter: str,
         target: str, parameters: List[str]):
    """ Run the cookbook or resource on the host(s) specified.
    """

    cfg = ctx.obj["config"]

    bootstrap_settings = remoteenv.Settings(
        directory=cfg.getpath("bootstrap", "directory"),
        clean=cfg.get("bootstrap", "clean"),
    )
    _runner = runner.Runner(bootstrap_settings=bootstrap_settings)

    fact_cache_type = cfg.get("fact cache", "type").lower()
    if fact_cache_type == "memory":
        fact_cache = MemoryFactCache()
    elif fact_cache_type == "filesystem":
        fact_cache = FilesystemFactCache(
            cfg.getpath("fact cache", "directory"),
            cfg.getseconds("fact cache", "lifetime"),
        )

    cookbook_paths = []
    for path in cookbooks:
        cookbook_paths.append(os.path.realpath(path))

    formatter = outputs.pick_formatter(outputter)
    resource_params = kvparse.parse_many(parameters)
    logger.debug(f"KVparse parsed parameters {resource_params}")

    inv = ctx.obj["inventory"]

    if limit:
        logger.debug(f"Limiting inventory {inv.hosts} by filter `{limit}`")
        inv = inv.select(limit)

    if len(inv) == 0:
        logger.fatal(f"Inventory filter `{limit}` resulted in empty inventory")
        return False

    logger.debug("Resolving inventory tags")
    inv = inv.resolve_tags()

    logger.debug(f"Executing on inventory {inv.hosts}")

    _runner.gather_facts(inv, fact_cache=fact_cache)
    results = list(_runner.execute(inv, target, resource_params))
    _runner.close()

    print(formatter(results))
