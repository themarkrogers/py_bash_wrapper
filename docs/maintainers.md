# Notes for maintainers

Operational context for merging, releasing, and reviewing changes. User-facing setup remains in
[README.md](../README.md).

## Version source of truth

- **`VERSION`** at the repo root holds the canonical SemVer string **without** a `v` prefix.
  - This must be manually bumped on each branch before merging to `main`.
- **Git tags** use a **`v` prefix** (e.g., `v0.2.0`).
- **`py_bash.__version__`** comes from installed package metadata when available; from a checkout it can fall back to
  reading `VERSION`. See `py_bash/__init__.py`.

## Release path

- The high-level flow: bump `VERSION` on a branch, merge to `main`, then the
  [Tag and release from VERSION workflow](../.github/workflows/release-from-version.yml) creates the tag, GitHub
  Release, and PyPI upload when appropriate.
- See more details in [README.md](../README.md) (Versioning).

## PyPI publishing

Releases upload to [PyPI](https://pypi.org/project/py_bash/).

**Workflow and environment**

- Triggered on all pushes to `main`.
- GHA Workflow file: `.github/workflows/release-from-version.yml`.
- Job: `publish-pypi` uses GitHub environment **`pypi`**. Create that environment under the repository
  **Settings > Environments** if it does not exist yet. Optional: add required reviewers or wait timers for extra safety.

## CI

- **`.github/workflows/ci.yml`** runs on pushes to `main` and on pull requests: install via `make install`, `make lint`,
  `make build`, `twine check` on `dist/*`, smoke-install the wheel in a clean venv, then `make run-tests-terminal`.
- Failures there should be treated as merge blockers unless explicitly waived with a documented reason.

## Dependabot

- **`.github/dependabot.yml`** opens weekly PRs for pip dependencies and GitHub Actions, with grouping and labels.
- Reviewer and label conventions are defined in that file; keep dependency bumps scoped and CI-green.

## Security and shell usage

- **`run_bash`** executes a string through the system Bash. Never pass untrusted or externally controlled strings as the
  command body.
- Prefer **`run_command`** with a fixed `argv` when shell features are not required. Patterns and caveats are spelled
  out in [usage_examples.md](usage_examples.md).
