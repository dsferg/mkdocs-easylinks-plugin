"""MkDocs EasyLinks Plugin - Simplified cross-referencing by filename."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mkdocs-easylinks-plugin")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
