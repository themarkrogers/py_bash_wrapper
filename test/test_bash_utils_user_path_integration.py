"""Integration checks for FEAT-01: same-user `user=` must preserve PATH (no sudo secure_path)."""

import os
import pwd
import shutil
import stat
from pathlib import Path

import pytest

import py_bash_wrapper.bash_utils as bash_utils


@pytest.mark.skipif(os.name != "posix", reason="user= switching is POSIX-only")
def test_run_command_same_user_finds_executable_on_custom_path(tmp_path: Path) -> None:
    """
    When `user=` matches the current process user, PATH from `path=` must reach the child so a unique binary in a temp
    directory is discoverable (e.g., via `which`).
    """
    bindir = tmp_path / "pbw_bin"
    bindir.mkdir()
    tool_name = "pbw_feat01_dummy_tool"
    tool_path = bindir / tool_name
    tool_path.write_text("#!/bin/sh\nprintf ok\n")
    tool_path.chmod(stat.S_IRWXU)

    which_cmd = shutil.which("which", path=os.environ.get("PATH", ""))
    if which_cmd is None:
        pytest.skip("`which` not found on PATH")

    user = pwd.getpwuid(os.getuid()).pw_name
    path_entries = [str(bindir), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]

    result = bash_utils.run_command([which_cmd, tool_name], user=user, path=path_entries, check=True)
    resolved = result.stdout.strip()
    assert resolved == str(tool_path)
