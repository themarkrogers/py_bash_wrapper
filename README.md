<!--- BADGES: START --->

[![GitHub license][#agpl-v3]][#license-gh-package]
[![Unit Tests][#ci-badge-img]][#ci-workflow]
[![Project Status][#status-active]][#status-licenses]
[![PyPI - Python Version][#pypi-project-python-version]][#pypi-package]
[![PyPI][#pypi-project-version]][#pypi-package]

[#agpl-v3]: https://img.shields.io/badge/License-AGPLv3-blue.svg
[#ci-badge-img]: https://github.com/themarkrogers/py_bash_wrapper/actions/workflows/ci.yml/badge.svg
[#ci-workflow]: https://github.com/themarkrogers/py_bash_wrapper/actions/workflows/ci.yml
[#license-gh-package]: https://www.gnu.org/licenses/agpl-3.0.en.html#license-text
[#pypi-package]: https://pypi.org/project/py_bash_wrapper/
[#pypi-project-python-version]: https://img.shields.io/pypi/pyversions/py_bash_wrapper
[#pypi-project-version]: https://img.shields.io/pypi/v/py_bash_wrapper
[#status-active]: http://opensource.box.com/badges/active.svg
[#status-inactive]: http://opensource.box.com/badges/inactive.svg
[#status-licenses]: http://opensource.box.com/badges

<!--- BADGES: END --->

# Py Bash Wrapper

![Logo](assets/py_bash_wrapper-logo.png)

## Description

**Py Bash Wrapper** helps Python developers run bash/shell/subprocess commands with two convenience functions:

* The **`run_command`** function takes in an argv **list** and provides no advances shell features likes pipes.
* The **`run_bash`** function provides real Bash (e.g., pipes, redirects, globs, etc.).

Results come back as **`CommandResult`** with stdout, stderr, exit code, and an **`ok`** flag;
The argument **`check=True`** will cause failures to raise a **`CommandError`**.

## Installation

From [PyPI](https://pypi.org/project/py_bash_wrapper/):

```bash
pip install py_bash_wrapper
```

## Documentation

- [Usage examples](docs/usage_examples.md) -- safe patterns, `run_command` vs. `run_bash`, errors and post-checks.
- [Project structure](docs/project_structure.md) -- where code, tests, and automation live.
- [Code style](docs/code_style.md) -- Ruff, Mypy, pytest, and conventions.
- [Maintainers](docs/maintainers.md) -- versions, CI, releases, security notes for shell APIs.
- [Plan / roadmap](docs/plan.md) -- upcoming tasks.

Full API details live in docstrings under `py_bash_wrapper/bash_utils.py` and in the usage doc above.

## Security note

**`run_bash` executes shell code.** Do not pass untrusted input as the Bash command string. Prefer **`run_command`**
with a fixed argv when shell features are not required. See [docs/usage_examples.md](docs/usage_examples.md).

## Quick start

Prerequisites: [Initial setup](#initial-setup) (`uv`, `make`, and a supported version of Python3).

```bash
make install
```

```python
from py_bash_wrapper.bash_utils import run_command, run_bash

print(run_command(["python", "-c", "print(1+1)"], check=True).stdout.strip())
print(run_bash("echo hello | wc -c", check=True).stdout.strip())
```

```bash
make run-tests
```

## Initial setup

Prerequisites:

* **uv** (package and tool runner):
  * macOS: `brew install uv` (see [Homebrew](https://brew.sh/) if needed).
  * Other: [Installing uv](https://docs.astral.sh/uv/getting-started/installation/) (official installer and package managers).
* **make**:
  * macOS: Xcode Command Line Tools or a build toolchain that provides `make`.
  * Linux: install `build-essential`.
  * Windows: use Git Bash, WSL, or another environment that provides `make`, or run the same `uv run ...` commands from
    the [Makefile](Makefile) by hand.
* **Python 3.12+**: install via OS package manager, via `uv` with `uv python install 3.12`, or via
  [python.org](https://www.python.org/downloads/).

## Common operations

* Install dependencies and pre-commit hooks: `make install`
* Run tests (coverage HTML): `make run-tests`
* Run tests (terminal coverage summary): `make run-tests-terminal`
* Lint and format check: `make lint`
* Lint with auto-fix and format write: `make lint-fix`
* Pre-commit gate (Ruff + pytest): `make pre-commit`
* Build sdist and wheel: `make build`
* Print version from `VERSION`: `make version-show`
* After a `v*` tag on `HEAD`, verify it matches `VERSION`: `make version-check-tag`

## Versioning

Releases follow [SemVer](https://semver.org/).
The canonical version string is the repo-root `VERSION` file (which contains no `v` prefix).
Git tags use a `v` prefix (e.g., `v0.2.0`). Packaging reads `VERSION` via `pyproject.toml` dynamic metadata.

To cut a release: bump `VERSION` on a branch, open a PR, and merge to `main`.
When `VERSION` changes on `main`, the **Tag and release from VERSION** workflow
(`.github/workflows/release-from-version.yml`) creates an annotated tag `vX.Y.Z` on that commit. Then, if that tag does
not already exist on the remote, and if no GitHub Release already exists for that same tag, then the workflow pushes it.
The same workflow then verifies tag/version consistency, builds the wheel and sdist artifacts, publishes a GitHub
Release immediately with auto-generated notes, and uploads the same artifacts to PyPI (Trusted Publishing; GitHub
environment `pypi`). Configure the publisher in PyPI before the first upload; see [docs/maintainers.md](docs/maintainers.md).

After a tag exists (or locally before pushing), `make version-check-tag` can be run to confirm the current `v*` tag
matches `VERSION`. CI runs `scripts/verify_version_matches_tag.py` on tag pushes for the same check.
