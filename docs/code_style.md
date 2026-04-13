# Code style

This project uses a small, enforced toolchain. For day-to-day commands, see [README.md](../README.md).

## Tooling

- **Ruff** -- lint and format. Configuration lives in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.
- **Line length:** 120 characters.
- **Python syntax baseline:** `target-version = "py311"` (code may run on 3.11+).
- **Mypy** -- static typing. `[tool.mypy]` excludes `build/` and `dist/`.

## Types and public API

- Public functions and methods should have **type hints** consistent with existing code in
  `py_bash_wrapper/bash_utils.py`.
- **Docstrings** for public API: use the same style as `bash_utils.py` (summary, `Args`/`Returns` where helpful).

## Code

- ToDo: Self-commenting code.
- ToDo: Optimize for maintainability, not performance.

## Tests

- Tests live under `test/` and are discovered by pytest (`[tool.pytest.ini_options]` in `pyproject.toml`).
- ToDo: Given, When, Then.

## What we avoid

- Drive-by refactoring or broad reformatting that is unrelated to the change at hand.
- Unrelated formatting-only edits in files you are not already touching for a clear reason.
