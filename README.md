<!--- BADGES: START --->

[![GitHub license][#agpl-v3]][#license-gh-package]
[![Unit Tests][#ci-badge-img]][#ci-workflow]
[![Project Status][#status-active]][#status-sources]
[![PyPI - Python Version][#pypi-project-python-version]][#pypi-package]
[![PyPI][#pypi-project-version]][#pypi-package]

[#agpl-v3]: https://img.shields.io/badge/License-AGPLv3-blue.svg
[#ci-badge-img]: https://github.com/themarkrogers/py_bash_wrapper/actions/workflows/ci.yml/badge.svg
[#ci-workflow]: https://github.com/themarkrogers/py_bash_wrapper/actions/workflows/ci.yml
[#license-gh-package]: https://www.gnu.org/licenses/agpl-3.0.en.html#license-text
[#pypi-package]: https://pypi.org/project/py_bash_wrapper/
[#pypi-project-python-version]: https://img.shields.io/pypi/pyversions/py_bash_wrapper
[#pypi-project-version]: https://img.shields.io/pypi/v/py_bash_wrapper
[#status-active]: https://opensource.box.com/badges/active.svg
[#status-inactive]: https://opensource.box.com/badges/inactive.svg
[#status-sources]: https://opensource.box.com/badges

<!--- BADGES: END --->

# Py-Bash-Wrapper

![(image of a cartoon snake on a `$_`)](https://github.com/themarkrogers/py_bash_wrapper/blob/main/assets/py_bash_wrapper-logo.png)

## Description

**Py Bash Wrapper** helps Python developers run bash/shell/subprocess commands with two convenience functions:

* The **`run_command`** function provides no advances shell features likes pipes. This function takes in either a string
  or an argv list.
* The **`run_bash`** function provides real Bash (e.g., pipes, redirects, globs, etc.). This function takes in a string.

Results come back as **`CommandResult`** with stdout, stderr, exit code, and an **`ok`** flag;
The argument **`check=True`** will cause failures to raise a **`CommandError`**.

## Installation

From [PyPI](https://pypi.org/project/py_bash_wrapper/):

```bash
pip install py_bash_wrapper
```

## Documentation

- [Usage examples](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/usage_examples.md) -- safe patterns, `run_command` vs. `run_bash`, errors and post-checks.
- [Project structure](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/project_structure.md) -- where code, tests, and automation live.
- [Code style](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/code_style.md) -- Ruff, Mypy, pytest, and conventions.
- [Maintainers](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/maintainers.md) -- versions, CI, releases, security notes for shell APIs.
- [Plan / roadmap](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/plan.md) -- upcoming tasks.

## Security note

**`run_bash` executes shell code.** Do not pass untrusted input as the Bash command string. Prefer **`run_command`**
with a fixed argv when shell features are not required. See [docs/usage_examples.md](https://github.com/themarkrogers/py_bash_wrapper/blob/main/docs/usage_examples.md).

## Initial setup

Prerequisites:

* **uv** (package and tool runner):
  * macOS: `brew install uv` (see [Homebrew](https://brew.sh/) if needed).
  * Other: [Installing uv](https://docs.astral.sh/uv/getting-started/installation/) (official installer and package managers).
* **make**:
  * macOS: Xcode Command Line Tools or a build toolchain that provides `make`.
  * Linux: install `build-essential`.
  * Windows: use Git Bash, WSL, or another environment that provides `make`, or run the same `uv run ...` commands from
    the [Makefile](https://github.com/themarkrogers/py_bash_wrapper/blob/main/Makefile) by hand.
* **Python 3.11+**: install via OS package manager, via `uv` with `uv python install 3.11`, or via
  [python.org](https://www.python.org/downloads/).

## Versioning

Releases follow [SemVer](https://semver.org/).
