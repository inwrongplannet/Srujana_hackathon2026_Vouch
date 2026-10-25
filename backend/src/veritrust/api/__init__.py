"""VeriTrust API package. The app lives in `veritrust.api.app` (`uvicorn veritrust.api.app:app`).

It is loaded lazily, so a router that never calls the OR-Tools optimizer (protocol and community
routes) can be imported and tested without loading it.
"""

import importlib

__all__ = ["create_app"]


def __getattr__(name: str):
    if name == "create_app":
        return importlib.import_module("veritrust.api.app").create_app
    raise AttributeError(f"module 'veritrust.api' has no attribute '{name}'")
