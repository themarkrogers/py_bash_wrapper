from unittest import TestCase
from unittest.mock import patch

import pytest

import py_bash.bash_utils as under_test


class PyBashTest(TestCase):
    def setUp(self):
        self.subprocess_run_patch = patch("py_bash.bash_utils.subprocess.run", autospec=True)

    def test_command_result_given_zero_exit_code_then_ok_is_true(self) -> None:
        # Given & When
        result = under_test.CommandResult(
            args=["echo", "hello"],
            command_display="echo hello",
            exit_code=0,
            stdout="hello\n",
            stderr="",
        )
        # Then
        assert result.ok is True

    def test_command_result_given_nonzero_exit_code_then_ok_if_false(self) -> None:
        # Given & When
        result = under_test.CommandResult(
            args=["false"],
            command_display="false",
            exit_code=1,
            stdout="",
            stderr="",
        )
        # Then
        assert result.ok is False

    def test_run_command_when_empty_command_raises(self):
        bash_command = ""
        with pytest.raises(ValueError):
            under_test.run_command(bash_command)
