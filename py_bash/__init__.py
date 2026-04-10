"""Py-Bash: helpers for running subprocesses and Bash from Python.

`__version__` is the public package version string (installed metadata or checkout fallback).
"""

from importlib.metadata import PackageNotFoundError, version


def _version() -> str:
    # After `pip install` / `uv sync`, the version comes from package metadata (same value as the VERSION file at
    # build time). If the package is not installed (e.g., running tests from a bare clone), then the metadata will be
    # missing, so read the repo-root VERSION file next to the `py_bash` package directory instead.
    try:
        return version("py_bash")
    except PackageNotFoundError:
        from pathlib import Path

        try:
            return (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            return "0+unknown"


__version__: str = _version()
