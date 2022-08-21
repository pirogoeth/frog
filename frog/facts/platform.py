# -*- coding: utf-8 -*-

import platform


def gather() -> dict:
    data = {}

    data["architecture"] = platform.architecture()
    data["machine"] = platform.machine()
    data["processor"] = platform.processor()
    data["python"] = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
    }
    data["system"] = platform.system()

    return {"platform": data}