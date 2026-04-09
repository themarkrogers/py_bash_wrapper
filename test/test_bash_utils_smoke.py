"""POSIX smoke tests that run real Bash via `run_bash` (skipped on non-posix)."""

import os

import pytest

import py_bash.bash_utils as under_test

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Smoke tests require a posix shell")


def test_run_bash_success_returns_expected_stdout() -> None:
    # Given
    command = "echo hi"
    # When
    result = under_test.run_bash(command)
    # Then
    assert result.exit_code == 0
    assert result.ok is True
    assert result.stdout.strip() == "hi"
    assert result.command_display == command


def test_run_bash_failure_with_check_false_returns_nonzero_result() -> None:
    # Given
    command = "false"
    # When
    result = under_test.run_bash(command, check=False)
    # Then
    assert result.ok is False
    assert result.exit_code != 0
    assert result.command_display == command
