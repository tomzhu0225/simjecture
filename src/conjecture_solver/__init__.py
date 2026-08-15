"""Core package for the Simjecture research runtime."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("simjecture")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
