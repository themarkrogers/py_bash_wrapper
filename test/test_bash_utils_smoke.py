"""POSIX smoke tests that run real Bash via `run_bash` (skipped on non-posix)."""

import os
from pathlib import Path

import pytest

import py_bash_wrapper.bash_utils as under_test

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


def test_run_bash_stream_callback_receives_lines_during_execution() -> None:
    # Given
    events: list[tuple[str, str]] = []

    def on_stream(stream_name: str, text: str) -> None:
        events.append((stream_name, text))

    command = "for i in 1 2 3; do echo line-$i; sleep 0.1; done"
    # When
    result = under_test.run_bash(command, stream_callback=on_stream, check=True)
    # Then
    assert result.exit_code == 0
    assert result.ok is True
    assert len(events) >= 3
    assert all(stream_name == "stdout" for stream_name, _ in events)
    joined = "".join(text for _, text in events)
    assert "line-1" in joined
    assert "line-2" in joined
    assert "line-3" in joined


def test_run_command_stdout_file_object_passthrough_writes_child_output(tmp_path: Path) -> None:
    # Given
    output_path = tmp_path / "stdout.log"
    # When
    with output_path.open("w", encoding="utf-8") as stdout_handle:
        result = under_test.run_command(["echo", "hello-from-child"], stdout=stdout_handle, check=True)
    # Then
    file_text = output_path.read_text(encoding="utf-8")
    assert file_text == "hello-from-child\n"
    assert result.exit_code == 0
    assert result.ok is True
    assert result.stdout == ""


def test_run_command_stderr_file_object_passthrough_writes_child_error(tmp_path: Path) -> None:
    # Given
    stderr_path = tmp_path / "stderr.log"
    command = ["/bin/bash", "-c", "echo boom >&2"]
    # When
    with stderr_path.open("w", encoding="utf-8") as stderr_handle:
        result = under_test.run_command(command, stderr=stderr_handle, check=True)
    # Then
    file_text = stderr_path.read_text(encoding="utf-8")
    assert file_text == "boom\n"
    assert result.exit_code == 0
    assert result.ok is True
    assert result.stderr == ""
