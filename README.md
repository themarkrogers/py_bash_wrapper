# Py-Bash

## Description

This library simplifies the use of Bash/Shell commands in Python.

## Development Setup

Install `uv` (if needed):

* macOS: `brew install uv`
* Other: `curl -LsSf https://astral.sh/uv/install.sh | sh`


Create and sync the project environment:

* `uv sync --extra dev --extra test`

## Run Tests

```bash
set -euo pipefail

uv sync --extra test
uv run pytest
```

## Lint and Format

```bash
uv run ruff check .
uv run ruff format .
```

## Pre-commit Hooks

Install hooks:

* `uv run pre-commit install`

Run against all files:

* `uv run pre-commit run --all-files`
