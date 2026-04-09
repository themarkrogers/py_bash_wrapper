from importlib.metadata import PackageNotFoundError, version


def _version() -> str:
    try:
        return version("py_bash")
    except PackageNotFoundError:
        from pathlib import Path

        try:
            return (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            return "0+unknown"


__version__: str = _version()
