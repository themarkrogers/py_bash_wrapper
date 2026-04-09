#!/usr/bin/env python3
"""Verify that a v* git tag matches the repo VERSION file (CI tag push or local exact tag)."""

import os
import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_version_file(root: Path) -> str:
    path = root / "VERSION"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        print("VERSION is empty", file=sys.stderr)
        sys.exit(1)
    return text.strip()


def _tag_from_github_ref() -> str | None:
    ref = os.environ.get("GITHUB_REF", "")
    m = re.match(r"^refs/tags/v(.+)$", ref)
    return m.group(1) if m else None


def _tag_from_git_exact(root: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", str(root), "describe", "--tags", "--exact-match", "HEAD"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    tag = r.stdout.strip()
    if tag.startswith("v"):
        return tag[1:]
    return tag


def main() -> None:
    root = _repo_root()
    expected = _read_version_file(root)
    actual = _tag_from_github_ref()
    if actual is None:
        actual = _tag_from_git_exact(root)
    if actual is None:
        print("Not a v* tag push (CI) and HEAD is not exactly tagged; skipping version check.", file=sys.stderr)
        sys.exit(0)
    if actual != expected:
        print(f"Mismatch: tag implies {actual!r}, VERSION file has {expected!r}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: tag and VERSION match ({expected!r})")


if __name__ == "__main__":
    main()
