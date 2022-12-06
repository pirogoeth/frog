# -*- coding: utf-8 -*-

import json
import logging
import shutil
import subprocess

log = logging.getLogger(__name__)


def get_tailscale_status() -> dict:
    tailscale_bin = shutil.which("tailscale")
    status_text = subprocess.check_output([tailscale_bin, "status", "-self", "-json"])
    return json.loads(status_text)


def gather() -> dict:
    try:
        status = get_tailscale_status()
        data = {
            "version": status["Version"],
            "online": status["Self"]["Online"],
            "capabilities": status["Self"]["Capabilities"],
            "dns_name": status["Self"]["DNSName"],
            "addresses": status["Self"]["TailscaleIPs"],
        }
        return {"tailscale": data}
    except subprocess.CalledProcessError:
        log.info("Tailscale status call failed")
        return None