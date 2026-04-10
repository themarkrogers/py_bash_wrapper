"""Packaging smoke tests: sdist/wheel build and install; `__version__` must match repo VERSION."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _build_dist(out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(out_dir)],
        cwd=str(_repo_root()),
        check=True,
        capture_output=True,
        text=True,
    )


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def test_build_produces_sdist_and_wheel(tmp_path: Path) -> None:
    # Given
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    # When
    _build_dist(dist_dir)
    # Then
    assert len(list(dist_dir.glob("*.whl"))) == 1
    assert len(list(dist_dir.glob("*.tar.gz"))) == 1


def test_built_wheel_installs_and_imports_with_expected_version(tmp_path: Path) -> None:
    # Given
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _build_dist(dist_dir)
    wheel_path = next(dist_dir.glob("*.whl"))
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, capture_output=True, text=True)
    venv_python = _venv_python(venv_dir)
    expected_version = (_repo_root() / "VERSION").read_text(encoding="utf-8").strip()
    # When
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", str(wheel_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    import_result = subprocess.run(
        [str(venv_python), "-c", "import py_bash_wrapper; print(py_bash_wrapper.__version__)"],
        check=True,
        capture_output=True,
        text=True,
    )
    # Then -- installed package must report the same string as the canonical VERSION file.
    assert import_result.stdout.strip() == expected_version
