# Project structure

Overview of the repository layout for contributors. Packaging rules determine what ships in the wheel; not every
directory is part of the installable package.

## Layout

| Path                 | Role                                                                                     |
|----------------------|------------------------------------------------------------------------------------------|
| `.github/workflows/` | CI (`ci.yml`); release + PyPI publish (`release-from-version.yml`, Trusted Publishing).  |
| `assets/`            | Static assets such as the logo referenced from the README.                               |
| `docs/`              | Project documentation (planning, style, this file). Not included in the published wheel. |
| `py_bash_wrapper/`   | Library package: public API (e.g., `run_command`, `run_bash`, `CommandResult`).          |
| `scripts/`           | Maintainer utilities (e.g., version/tag verification for CI or local use).               |
| `test/`              | Pytest tests and coverage targets for `py_bash_wrapper`.                                 |

## What is excluded from the wheel

`pyproject.toml` configures setuptools package discovery with `exclude` for paths such as `docs`, `scripts`, `test*`,
`assets`, and build artifacts. Expect **only** the `py_bash_wrapper` package (and its data, if any) inside the installed
distribution, not the full repo tree.
