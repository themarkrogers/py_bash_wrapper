"""Unit tests for `py_bash_wrapper.bash_utils` (mocked subprocess, timeouts, user/sudo branches, and helpers)."""

import os as real_os
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest

import py_bash_wrapper.bash_utils as under_test


def _completed(return_code: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    """Minimal mock return value for `subprocess.run`."""
    return subprocess.CompletedProcess(args=[], returncode=return_code, stdout=stdout, stderr=stderr)


class TestCommandResult(TestCase):
    """Tests for `CommandResult` and its `ok` property."""

    def test_given_zero_exit_code_then_ok_is_true(self) -> None:
        # Given
        args = ["echo", "hello"]
        display = "echo hello"
        exit_code = 0
        # When
        result = under_test.CommandResult(
            args=list(args),
            command_display=display,
            exit_code=exit_code,
            stdout="hello\n",
            stderr="",
        )
        # Then
        assert result.ok is True
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.args == args

    def test_given_positive_exit_code_then_ok_is_false(self) -> None:
        # Given
        exit_code = 1
        # When
        result = under_test.CommandResult(
            args=["false"],
            command_display="false",
            exit_code=exit_code,
            stdout="",
            stderr="err",
        )
        # Then
        assert result.ok is False

    def test_given_negative_exit_code_then_ok_is_false(self) -> None:
        # Given
        exit_code = -1
        # When
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=exit_code,
            stdout="",
            stderr="",
        )
        # Then
        assert result.ok is False

    def test_given_multiline_stdout_then_fields_are_preserved(self) -> None:
        # Given
        text = "line1\nline2\n"
        # When
        result = under_test.CommandResult(
            args=["x"],
            command_display="x",
            exit_code=0,
            stdout=text,
            stderr="warn\n",
        )
        # Then
        assert result.stdout == text
        assert result.stderr == "warn\n"


class TestCommandError(TestCase):
    """Tests for `CommandError`."""

    def test_given_message_and_result_then_str_matches_message(self) -> None:
        # Given
        inner = under_test.CommandResult(
            args=["false"],
            command_display="false",
            exit_code=1,
            stdout="",
            stderr="boom",
        )
        message = "Command failed with exit code 1: false"
        # When
        exc = under_test.CommandError(message, inner)
        # Then
        assert str(exc) == message
        assert exc.args[0] == message

    def test_given_message_and_result_then_result_attribute_is_set(self) -> None:
        # Given
        inner = under_test.CommandResult(
            args=["true"],
            command_display="true",
            exit_code=0,
            stdout="ok",
            stderr="",
        )
        # When
        exc = under_test.CommandError("custom", inner)
        # Then
        assert exc.result is inner
        assert exc.result.stdout == "ok"


class TestMakePreExecFunctionToRunAsUser(TestCase):
    """Tests for `_make_pre_exec_function_to_run_as_user`."""

    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam", autospec=True)
    @patch("py_bash_wrapper.bash_utils.os.setuid", autospec=True)
    @patch("py_bash_wrapper.bash_utils.os.setgid", autospec=True)
    def test_given_user_when_calling_returned_preexec_then_sets_ids_and_home(
        self, mock_setgid: MagicMock, mock_setuid: MagicMock, mock_getpwnam: MagicMock
    ) -> None:
        # Given
        fake_passwd_entry = MagicMock()
        fake_passwd_entry.pw_uid = 1234
        fake_passwd_entry.pw_gid = 4321
        fake_passwd_entry.pw_dir = "/home/example"
        mock_getpwnam.return_value = fake_passwd_entry
        with patch.dict("py_bash_wrapper.bash_utils.os.environ", {"HOME": "/old/home"}, clear=True):
            # When
            pre_exec_function = under_test._make_pre_exec_function_to_run_as_user("example")
            pre_exec_function()
            # Then
            mock_getpwnam.assert_called_once_with("example")
            mock_setgid.assert_called_once_with(4321)
            mock_setuid.assert_called_once_with(1234)
            assert under_test.os.environ["HOME"] == "/home/example"


class TestRunCommand(TestCase):
    """Tests for `run_command`."""

    def test_given_empty_list_command_then_raises_value_error(self) -> None:
        # Given
        argv: list[str] = []
        # When & Then
        with pytest.raises(ValueError, match="command must not be empty"):
            under_test.run_command(argv)

    def test_given_empty_string_command_then_raises_value_error(self) -> None:
        # Given
        command = ""
        # When & Then
        with pytest.raises(ValueError, match="command must not be empty"):
            under_test.run_command(command)

    def test_given_sequence_with_non_string_elements_then_raises_value_error(self) -> None:
        # Given
        bad: list[object] = ["echo", 1]
        # When & Then
        with pytest.raises(ValueError, match="command must be either"):
            under_test.run_command(cast("list[str]", bad))

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_successful_process_then_result_ok_and_output_set(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(return_code=0, stdout="hi\n", stderr="")
        argv = ["echo", "hi"]
        # When
        result = under_test.run_command(argv)
        # Then
        assert result.ok is True
        assert result.stdout == "hi\n"
        assert result.stderr == ""
        assert result.command_display
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_string_command_then_splits_with_shlex_like_argv_list(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(return_code=0, stdout="hi\n", stderr="")
        command = 'echo "hi there"'
        expected_argv = ["echo", "hi there"]
        # When
        result = under_test.run_command(command)
        # Then
        assert result.ok is True
        assert result.stdout == "hi\n"
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == expected_argv
        assert result.args == expected_argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_nonzero_exit_and_check_false_then_no_raise(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(return_code=7, stdout="", stderr="nope")
        argv = ["cmd"]
        # When
        result = under_test.run_command(argv, check=False)
        # Then
        assert result.ok is False
        assert result.exit_code == 7
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_nonzero_exit_and_check_true_then_raises_command_error(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        return_code = 2
        mock_subprocess_run.return_value = _completed(return_code=return_code, stdout="", stderr="")
        argv = ["x"]
        # When & Then
        with pytest.raises(under_test.CommandError) as ctx:
            under_test.run_command(argv, check=True)
        assert ctx.value.result is not None
        assert ctx.value.result.exit_code == return_code
        assert f"exit code {return_code}" in str(ctx.value)
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_timeout_expired_then_raises_timeout_error(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=["slow"], timeout=3.0)
        argv = ["slow"]
        # When & Then
        with pytest.raises(TimeoutError, match="timed out after 3"):
            under_test.run_command(argv, timeout=3.0)
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_env_and_path_then_subprocess_gets_merged_env(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        extra = {"FOO": "bar"}
        path_entries = ["/a", "/b"]
        argv = ["tool"]
        # When
        under_test.run_command(argv, env=extra, path=path_entries)
        # Then
        env_passed = mock_subprocess_run.call_args.kwargs["env"]
        assert env_passed["FOO"] == "bar"
        assert env_passed["PATH"] == real_os.pathsep.join(path_entries)
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_path_string_then_path_env_is_string(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = ["tool"]
        # When
        under_test.run_command(argv, path="/only/here")
        # Then
        assert mock_subprocess_run.call_args.kwargs["env"]["PATH"] == "/only/here"
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_cwd_path_then_cwd_passed_as_str(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        tmp = Path("/tmp/py_bash_wrapper_test_cwd")
        argv = ["ls"]
        # When
        under_test.run_command(argv, cwd=tmp)
        # Then
        assert mock_subprocess_run.call_args.kwargs["cwd"] == str(tmp)
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_input_text_then_passed_to_subprocess(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "out", "")
        argv = ["cat"]
        # When
        under_test.run_command(argv, input_text="hello")
        # Then
        assert mock_subprocess_run.call_args.kwargs["input"] == "hello"
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_inherit_env_false_then_env_starts_minimal(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = ["env"]
        # When
        under_test.run_command(argv, env={"ONLY": "1"}, inherit_env=False)
        # Then
        env_passed = mock_subprocess_run.call_args.kwargs["env"]
        assert env_passed == {"ONLY": "1"}
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_empty_path_entries_then_path_env_is_empty_string(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = ["tool"]
        # When
        under_test.run_command(argv, path=[])
        # Then
        env_passed = mock_subprocess_run.call_args.kwargs["env"]
        assert "PATH" in env_passed
        assert env_passed["PATH"] == ""
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_large_output_then_stdout_and_stderr_are_not_truncated(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        large_stdout = "A" * 10_000
        large_stderr = "B" * 10_000
        mock_subprocess_run.return_value = _completed(0, large_stdout, large_stderr)
        argv = ["tool"]
        # When
        result = under_test.run_command(argv)
        # Then
        assert result.ok is True
        assert result.stdout == large_stdout
        assert result.stderr == large_stderr
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_text_false_and_none_streams_then_result_streams_become_empty_strings(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        # Given
        mock_subprocess_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=None, stderr=None)
        argv = ["tool"]
        # When
        result = under_test.run_command(argv, text=False)
        # Then
        assert result.ok is True
        assert result.stdout == ""
        assert result.stderr == ""
        assert mock_subprocess_run.call_args.kwargs["text"] is False
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_on_non_posix_then_raises_runtime_error(
        self, mock_os: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given
        mock_os.name = "nt"
        mock_os.environ = {}
        # When & Then
        with pytest.raises(RuntimeError, match="only supported on Unix"):
            under_test.run_command(["cmd"], user="someone")
        mock_subprocess_run.assert_not_called()

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils._make_pre_exec_function_to_run_as_user", return_value=lambda: None)
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_as_root_then_pre_exec_fn_set(
        self, mock_os: MagicMock, mock_getpwnam: MagicMock, make_pre_exec_fn: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given
        mock_os.name = "posix"
        mock_os.geteuid.return_value = 0
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.return_value = SimpleNamespace(pw_uid=65534, pw_gid=65534, pw_dir="/nonexistent")
        mock_subprocess_run.return_value = _completed(0, "ok", "")
        argv = ["id"]
        # When
        under_test.run_command(argv, user="nobody")
        # Then
        assert mock_subprocess_run.call_args.kwargs["preexec_fn"] is not None
        make_pre_exec_fn.assert_called_once_with("nobody")
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.shutil.which", return_value="/usr/bin/sudo")
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_non_root_with_sudo_then_argv_prefixed(
        self, mock_os: MagicMock, mock_getpwnam: MagicMock, mock_which: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given: effective UID must differ from the passwd entry so we exercise the sudo branch (not same-user).
        mock_os.name = "posix"
        mock_os.geteuid.return_value = 1000
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.return_value = SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_dir="/home/alice")
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = ["true"]
        expected_sudo = "/usr/bin/sudo"
        # When
        under_test.run_command(argv, user="alice")
        # Then
        found_argv = mock_subprocess_run.call_args[0][0]
        assert found_argv[:5] == [expected_sudo, "-H", "-u", "alice", "--"]
        assert found_argv[5:] == argv
        mock_which.assert_called_once()
        mock_subprocess_run.assert_called_once()

    @patch("py_bash_wrapper.bash_utils.shutil.which", return_value=None)
    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_non_root_without_sudo_then_raises(
        self, mock_os: MagicMock, mock_getpwnam: MagicMock, mock_subprocess_run: MagicMock, mock_which: MagicMock
    ) -> None:
        # Given: target user differs from EUID so the implementation still attempts the sudo path.
        mock_os.name = "posix"
        mock_os.geteuid.return_value = 500
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.return_value = SimpleNamespace(pw_uid=501, pw_gid=501, pw_dir="/home/bob")
        argv = ["true"]
        # When & Then
        with pytest.raises(RuntimeError, match="sudo not found"):
            under_test.run_command(argv, user="bob")
        mock_which.assert_called_once()
        mock_subprocess_run.assert_not_called()

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.shutil.which")
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_matches_euid_then_runs_without_sudo(
        self, mock_os: MagicMock, mock_getpwnam: MagicMock, mock_which: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given: same effective UID as passwd entry -- must not wrap in sudo so merged PATH/env reach the child.
        mock_os.name = "posix"
        mock_os.pathsep = real_os.pathsep
        mock_os.geteuid.return_value = 1000
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.return_value = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir="/home/selfuser")
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = ["which", "hisat2"]
        extra_path = "/opt/hisat2-2.2.1"
        # When
        under_test.run_command(argv, user="selfuser", path=["/bin", "/usr/bin", extra_path])
        # Then
        mock_which.assert_not_called()
        assert mock_subprocess_run.call_args[0][0] == argv
        assert mock_subprocess_run.call_args.kwargs.get("preexec_fn") in (None, False)
        child_env = mock_subprocess_run.call_args.kwargs["env"]
        assert extra_path in child_env.get("PATH", "")

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.shutil.which", return_value="/usr/bin/sudo")
    @patch("py_bash_wrapper.bash_utils.os")
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    def test_given_unknown_username_then_raises_value_error(
        self, mock_getpwnam: MagicMock, mock_os: MagicMock, mock_which: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given
        mock_os.name = "posix"
        mock_os.geteuid.return_value = 1000
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.side_effect = KeyError("getpwnam(): name not found: 'nonesuch_pbw_user'")
        # When & Then: library should surface a clear error before subprocess or sudo.
        with pytest.raises(ValueError, match="nonesuch_pbw_user"):
            under_test.run_command(["true"], user="nonesuch_pbw_user")
        mock_subprocess_run.assert_not_called()

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    @patch("py_bash_wrapper.bash_utils.pwd.getpwnam")
    @patch("py_bash_wrapper.bash_utils.os")
    def test_given_user_root_when_euid_root_then_runs_without_preexec(
        self, mock_os: MagicMock, mock_getpwnam: MagicMock, mock_subprocess_run: MagicMock
    ) -> None:
        # Given: root invoking as root should not use preexec_fn so the merged environment is preserved unchanged.
        mock_os.name = "posix"
        mock_os.geteuid.return_value = 0
        mock_os.environ = dict(real_os.environ)
        mock_getpwnam.return_value = SimpleNamespace(pw_uid=0, pw_gid=0, pw_dir="/root")
        mock_subprocess_run.return_value = _completed(0, "root", "")
        argv = ["whoami"]
        # When
        under_test.run_command(argv, user="root")
        # Then
        assert mock_subprocess_run.call_args.kwargs.get("preexec_fn") in (None, False)
        assert mock_subprocess_run.call_args[0][0] == argv


class TestRunBash(TestCase):
    """Tests for `run_bash`."""

    bin_bash = "/bin/bash"
    homebrew_bash = "/opt/homebrew/bin/bash"

    def test_given_empty_command_then_raises_value_error(self) -> None:
        # Given
        command = ""
        # When & Then
        with pytest.raises(ValueError, match="must not be empty"):
            under_test.run_bash(command)

    def test_given_whitespace_only_command_then_raises_value_error(self) -> None:
        # Given
        command = "   \t\n"
        # When & Then
        with pytest.raises(ValueError, match="must not be empty"):
            under_test.run_bash(command)

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_strict_true_then_script_includes_pipefail(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        user_command = "echo hi"
        # When
        under_test.run_bash(user_command, strict=True)
        # Then
        found_argv = mock_subprocess_run.call_args[0][0]
        script = found_argv[-1]
        assert script.startswith("set -euo pipefail\n")
        assert user_command in script
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0][0] == self.bin_bash
        assert mock_subprocess_run.call_args[0][0][-1].split("\n")[-1] == user_command

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_strict_false_then_script_has_no_pipefail_prefix(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        body = "echo hi"
        # When
        under_test.run_bash(body, strict=False)
        # Then
        found_argv = mock_subprocess_run.call_args[0][0]
        assert found_argv[-1] == body
        assert "pipefail" not in found_argv[-1]
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0][0] == self.bin_bash
        assert mock_subprocess_run.call_args[0][0][-1].split("\n")[-1] == body

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_login_true_then_bash_argv_includes_l_flag(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        argv = "true"
        # When
        under_test.run_bash(argv, login=True)
        # Then
        found_argv = mock_subprocess_run.call_args[0][0]
        assert found_argv[0] == self.bin_bash
        assert "-l" in found_argv
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0][0] == self.bin_bash
        assert mock_subprocess_run.call_args[0][0][-1].split("\n")[-1] == argv

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_custom_shell_path_then_used_as_argv_zero(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "", "")
        custom = self.homebrew_bash
        # When
        under_test.run_bash(":", path_to_shell_executable=custom)
        # Then
        assert mock_subprocess_run.call_args[0][0][0] == custom
        mock_subprocess_run.assert_called_once()

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_success_then_command_display_is_user_string(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(0, "x", "")
        bash_line = "echo ok | cat"
        # When
        result = under_test.run_bash(bash_line)
        # Then
        assert result.command_display == bash_line
        assert result.ok is True
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0][0] == self.bin_bash
        assert mock_subprocess_run.call_args[0][0][-1].split("\n")[-1] == bash_line

    @patch("py_bash_wrapper.bash_utils.subprocess.run", autospec=True)
    def test_given_failure_and_check_true_then_raises_command_error(self, mock_subprocess_run: MagicMock) -> None:
        # Given
        mock_subprocess_run.return_value = _completed(1, "", "err")
        snippet = "false"
        # When & Then
        with pytest.raises(under_test.CommandError) as ctx:
            under_test.run_bash(snippet, check=True)
        assert ctx.value.result is not None
        assert ctx.value.result.command_display == snippet
        assert "Bash command failed" in str(ctx.value)
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[0][0][0] == self.bin_bash
        assert mock_subprocess_run.call_args[0][0][-1].split("\n")[-1] == snippet


class TestCheckResultForText(TestCase):
    """Tests for `check_result_for_text`."""

    def test_given_clean_output_then_no_raise(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="all good",
            stderr="",
        )
        # When & Then
        under_test.check_result_for_text(result, error_substrings=["ERROR"])

    def test_given_marker_in_stdout_case_insensitive_then_raises(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="something FATAL happened",
            stderr="",
        )
        # When & Then
        with pytest.raises(under_test.CommandError) as ctx:
            under_test.check_result_for_text(result, error_substrings=["fatal"])
        assert "error marker" in str(ctx.value).lower()
        assert ctx.value.result is result

    def test_given_marker_in_stderr_then_raises(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="",
            stderr="oops ERROR_OOPS tail",
        )
        # When & Then
        with pytest.raises(under_test.CommandError, match="ERROR_OOPS"):
            under_test.check_result_for_text(result, error_substrings=["ERROR_OOPS"])

    def test_given_predicate_true_then_raises(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="x",
            stderr="y",
        )

        def predicate(out: str, err: str) -> bool:
            return out == "x" and err == "y"

        # When & Then
        with pytest.raises(under_test.CommandError, match="custom error predicate"):
            under_test.check_result_for_text(result, error_predicate=predicate)

    def test_given_predicate_false_then_no_raise(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="ok",
            stderr="",
        )
        # When & Then
        under_test.check_result_for_text(result, error_predicate=lambda _o, _e: False)

    def test_given_empty_substrings_list_then_no_raise(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="anything",
            stderr="",
        )
        # When & Then
        under_test.check_result_for_text(result, error_substrings=[])

    def test_given_empty_output_and_no_markers_then_no_raise(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="",
            stderr="",
        )
        # When & Then
        under_test.check_result_for_text(result, error_substrings=None)

    def test_given_multiple_markers_then_first_matching_marker_is_reported(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="line has SECOND marker",
            stderr="",
        )
        markers = ["first", "second", "third"]
        # When & Then
        with pytest.raises(under_test.CommandError) as ctx:
            under_test.check_result_for_text(result, error_substrings=markers)
        assert "second" in str(ctx.value).lower()
        assert "third" not in str(ctx.value).lower()

    def test_given_predicate_raises_then_exception_propagates(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["a"],
            command_display="a",
            exit_code=0,
            stdout="out",
            stderr="err",
        )

        def predicate(_out: str, _err: str) -> bool:
            raise ValueError("predicate broke")

        # When & Then
        with pytest.raises(ValueError, match="predicate broke"):
            under_test.check_result_for_text(result, error_predicate=predicate)


class TestRequireSuccess(TestCase):
    """Tests for `require_success`."""

    def test_given_ok_result_then_returns_same_instance(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["true"],
            command_display="true",
            exit_code=0,
            stdout="",
            stderr="",
        )
        # When
        out = under_test.require_success(result)
        # Then
        assert out is result

    def test_given_failed_result_then_raises_command_error(self) -> None:
        # Given
        result = under_test.CommandResult(
            args=["false"],
            command_display="false",
            exit_code=9,
            stdout="",
            stderr="e",
        )
        # When & Then
        with pytest.raises(under_test.CommandError) as ctx:
            under_test.require_success(result)
        assert ctx.value.result is result
        assert "exit code 9" in str(ctx.value)


class TestTerminateProcessGroup(TestCase):
    """Tests for `terminate_process_group`."""

    @patch("py_bash_wrapper.bash_utils.os.killpg")
    def test_given_process_with_pid_then_killpg_with_sigterm(self, mock_killpg: MagicMock) -> None:
        # Given
        proc = MagicMock()
        proc.pid = 4242
        # When
        under_test.terminate_process_group(cast(subprocess.Popen[str], proc))
        # Then
        mock_killpg.assert_called_once_with(4242, signal.SIGTERM)

    @patch("py_bash_wrapper.bash_utils.os.killpg", side_effect=ProcessLookupError)
    def test_given_process_lookup_error_then_no_propagate(self, mock_killpg: MagicMock) -> None:
        # Given
        proc = MagicMock()
        proc.pid = 999
        # When & Then
        under_test.terminate_process_group(cast(subprocess.Popen[str], proc))
        mock_killpg.assert_called_once()
