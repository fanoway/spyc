"""spyc (pronounced spicy) module."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("spyc-spc")
except importlib.metadata.PackageNotFoundError:
    __version__ = "None"
