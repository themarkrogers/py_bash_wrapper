"""
py_bash_wrapper/bash_utils.py

Reusable helpers for running commands and Bash snippets from Python.

Design goals:
- Safe default for normal commands: pass argv, no shell.
- Explicit Bash mode for shell features: pipes, redirects, subshells, etc.
- Structured result object with stdout, stderr, exit code, and success flag.
- Optional custom environment / PATH.
- Optional run-as-user support on Unix:
  - If the effective UID already matches the target user, run the command directly (no sudo, no preexec_fn) so PATH and
    env are preserved.
  - If running as root for a different user, drop privileges via preexec_fn.
  - Otherwise, use sudo if available and allowed (sudo may apply secure_path and override PATH).
- Good errors and type hints.
"""

import os
import pwd
import shlex
import shutil
import signal
import subprocess
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any


@dataclass(slots=True)
class CommandResult:
    """Structured command result."""

    args: list[str]
    command_display: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class CommandError(RuntimeError):
    """Raised when a command fails and check=True."""

    result: CommandResult | None = None

    def __init__(self, message: str, result: CommandResult) -> None:
        super().__init__(message)
        self.result = result


def _merge_env(
    env: Mapping[str, str] | None = None,
    *,
    path: str | Sequence[str] | None = None,
    inherit_env: bool = True,
) -> dict[str, str]:
    """
    Build the environment for a subprocess.

    Args:
        env: Additional / overriding environment variables.
        path: If provided, sets PATH. Can be a string or a sequence of path entries.
        inherit_env: If True, start from os.environ. If False, start empty.

    Returns:
        A new environment dict.
    """
    merged_env: dict[str, str] = dict(os.environ) if inherit_env else {}
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    if path is not None:
        if isinstance(path, str):
            merged_env["PATH"] = path
        else:
            merged_env["PATH"] = os.pathsep.join(str(p) for p in path)
    return merged_env


def _quote_join(argv: Sequence[str]) -> str:
    """Human-readable shell-quoted rendering of argv for logs/errors."""
    return subprocess.list2cmdline(list(argv))


def _passwd_uid_for_username(username: str) -> int:
    """Return the passwd database UID for a Unix login name."""
    try:
        return pwd.getpwnam(username).pw_uid
    except KeyError as exc:
        raise ValueError(f"No passwd entry for Unix user {username!r}") from exc


def _make_pre_exec_function_to_run_as_user(user: str) -> Callable[[], None]:
    """
    Create a preexec_fn that drops privileges to the target user on Unix.

    This only works when the current process has permission to do so,
    typically when running as root.
    """
    pw = pwd.getpwnam(user)
    target_uid = pw.pw_uid
    target_gid = pw.pw_gid
    home = pw.pw_dir

    def _preexec() -> None:
        os.setgid(target_gid)
        os.setuid(target_uid)
        os.environ["HOME"] = home

    return _preexec


def _build_bash_command(
    command: str,
    *,
    path_to_shell_executable: str,
    login: bool,
    strict: bool,
) -> list[str]:
    """
    Build 'argv' (a.k.a. the shell command) for running a command through Bash.

    Args:
        login: login=True uses bash -l -c, which can help pick up profile files.
        strict: strict=True prepends: set -euo pipefail
    """
    if strict:
        script = f"set -euo pipefail\n{command}"
    else:
        script = command

    argv: list[str] = [path_to_shell_executable]
    if login:
        argv.append("-l")
    argv.extend(["-c", script])
    return argv


def check_result_for_text(
    result: CommandResult,
    *,
    error_substrings: Sequence[str] | None = None,
    error_predicate: Callable[[str, str], bool] | None = None,
) -> None:
    """
    Raise CommandError if stdout/stderr contain any of the error_substrings, even when the exit code is 0.

    This replaces brittle ad hoc post-processing logic.
    """
    stdout = result.stdout
    stderr = result.stderr
    if error_substrings:
        combined = f"{stdout}\n{stderr}"
        for error_signal in error_substrings:
            if error_signal.lower() in combined.lower():
                raise CommandError(f"Command output contained an error marker: {error_signal}", result)
    if error_predicate and error_predicate(stdout, stderr):
        raise CommandError("Command output matched custom error predicate", result)


def require_success(result: CommandResult) -> CommandResult:
    """Raise CommandError if the result is not successful; otherwise return it."""
    if not result.ok:
        raise CommandError(f"Command failed with exit code {result.exit_code}: {result.command_display}", result)
    return result


def run_bash(
    command: str,
    *,
    env: Mapping[str, str] | None = None,
    path: str | Sequence[str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
    input_text: str | None = None,
    check: bool = False,
    inherit_env: bool = True,
    user: str | None = None,
    login: bool = False,
    strict: bool = True,
    path_to_shell_executable: str = "/bin/bash",
    shell: bool = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = None,
    stream_callback: Callable[[str, str], None] | None = None,
) -> CommandResult:
    """
    Run a real Bash command string.

    This provides shell features such as:
    - pipes
    - redirects
    - subshells: $(...), (...)
    - globbing
    - brace expansion
    - && / || / ; / here-docs

    Args:
        command: Bash command string.
        env: Extra environment variables.
        path: Override PATH.
        cwd: Working directory.
        timeout: Timeout in seconds.
        input_text: Optional stdin text.
        check: Raise CommandError if exit code != 0.
        inherit_env: Whether to start from current os.environ.
        user: Target Unix username; semantics match `run_command(..., user=...)`.
        login: Use a login shell (`bash -l -c`) so profile files may be sourced.
        strict: Prepend `set -euo pipefail`.
        path_to_shell_executable: Path to bash.

    Returns:
        CommandResult
    """
    if not command.strip():
        raise ValueError("'command' must not be empty or only whitespace.")
    bash_argv = _build_bash_command(
        command, path_to_shell_executable=path_to_shell_executable, login=login, strict=strict
    )
    result = run_command(
        bash_argv,
        env=env,
        path=path,
        cwd=cwd,
        timeout=timeout,
        input_text=input_text,
        check=False,
        inherit_env=inherit_env,
        user=user,
        shell=shell,
        stdout=stdout,
        stderr=stderr,
        stream_callback=stream_callback,
    )
    # Show the caller's Bash source in errors/logs; args still reflect the real argv (bash -c script).
    result = CommandResult(
        args=result.args,
        command_display=command,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    if check and not result.ok:
        raise CommandError(f"Bash command failed with exit code {result.exit_code}: {command}", result)
    return result


def run_command(
    command: str | Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    path: str | Sequence[str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
    input_text: str | None = None,
    check: bool = False,
    text: bool = True,
    inherit_env: bool = True,
    user: str | None = None,
    shell: bool = False,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = None,
    stream_callback: Callable[[str, str], None] | None = None,
) -> CommandResult:
    """
    Run a normal command safely without a shell.

    Use this for commands that do NOT need pipes, redirects, subshells, globbing,
    shell variables, or other shell syntax.

    Args:
        command: Command argv, e.g., either "docker inspect my-container" or ["docker", "inspect", "my-container"].
        env: Extra environment variables.
        path: Override PATH.
        cwd: Working directory.
        timeout: Timeout in seconds.
        input_text: Optional stdin text.
        check: Raise CommandError if exit code != 0.
        text: Capture text output. Defaults to True.
        inherit_env: Whether to start from the current os.environ.
        user: Target Unix username to run as, best-effort. If the effective UID already matches that user, the command
            runs without sudo or privilege-drop so your merged environment (including PATH) is passed through unchanged.
            If sudo is used for a different user, many sudoers configurations set secure_path, which can replace PATH
            regardless of the env dict passed here. Unknown usernames raise ValueError.

    Returns:
        CommandResult
    """
    if not command:
        raise ValueError("command must not be empty")
    if isinstance(command, str):
        argv: Sequence[str] = shlex.split(command)
    elif isinstance(command, Sequence) and all(isinstance(arg, str) for arg in command):
        argv = command
    else:
        raise ValueError("command must be either a `str` or a `Sequence[str]`")

    merged_env = _merge_env(env, path=path, inherit_env=inherit_env)

    pre_exec_function_to_run_as_user: Callable[[], None] | None = None
    final_argv = list(argv)

    if user:
        if os.name != "posix":
            raise RuntimeError("user switching is only supported on Unix-like systems")
        target_uid = _passwd_uid_for_username(user)
        euid = os.geteuid()
        if euid == target_uid:
            # Already the target user: avoid sudo (secure_path) and avoid redundant preexec_fn.
            pre_exec_function_to_run_as_user = None
        elif euid == 0:
            pre_exec_function_to_run_as_user = _make_pre_exec_function_to_run_as_user(user)
        else:
            sudo_path = shutil.which("sudo", path=merged_env.get("PATH"))
            if sudo_path is None:
                raise RuntimeError("Cannot run as another user: not root and sudo not found in PATH")
            final_argv = [sudo_path, "-H", "-u", user, "--", *final_argv]

    if stream_callback is None:
        run_kwargs: dict[str, Any] = {
            "input": input_text,
            "text": text,
            "cwd": str(cwd) if cwd is not None else None,
            "env": merged_env,
            "timeout": timeout,
            "check": False,
            "preexec_fn": pre_exec_function_to_run_as_user,
            "shell": shell,
        }
        if stdout is None and stderr is None:
            run_kwargs["capture_output"] = True
        else:
            run_kwargs["stdout"] = stdout
            run_kwargs["stderr"] = stderr

        try:
            proc = subprocess.run(final_argv, **run_kwargs)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"Command timed out after {timeout}s: {_quote_join(final_argv)}") from exc

        result = CommandResult(
            args=final_argv,
            command_display=_quote_join(final_argv),
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
    else:
        stdin_target: int | None = subprocess.PIPE if input_text is not None else None
        popen_stdout: int | IO[str] = subprocess.PIPE if stdout is None else stdout
        popen_stderr: int | IO[str] = subprocess.PIPE if stderr is None else stderr
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def _read_stream(pipe: Any, stream_name: str, sink: list[str]) -> None:
            if pipe is None:
                return
            while True:
                chunk = pipe.readline()
                if chunk in ("", b""):
                    break
                text_chunk = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="replace")
                sink.append(text_chunk)
                stream_callback(stream_name, text_chunk)

        try:
            popen_proc = subprocess.Popen(
                final_argv,
                stdin=stdin_target,
                stdout=popen_stdout,
                stderr=popen_stderr,
                text=text,
                cwd=str(cwd) if cwd is not None else None,
                env=merged_env,
                preexec_fn=pre_exec_function_to_run_as_user,
                shell=shell,
                start_new_session=True,
            )
        except OSError as exc:
            raise RuntimeError(f"Failed to start command: {_quote_join(final_argv)}") from exc

        if input_text is not None and popen_proc.stdin is not None:
            popen_proc.stdin.write(input_text)
            popen_proc.stdin.close()

        threads: list[threading.Thread] = []
        if popen_proc.stdout is not None:
            threads.append(threading.Thread(target=_read_stream, args=(popen_proc.stdout, "stdout", stdout_chunks)))
        if popen_proc.stderr is not None:
            threads.append(threading.Thread(target=_read_stream, args=(popen_proc.stderr, "stderr", stderr_chunks)))

        for worker in threads:
            worker.daemon = True
            worker.start()

        try:
            exit_code = popen_proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            terminate_process_group(popen_proc)
            raise TimeoutError(f"Command timed out after {timeout}s: {_quote_join(final_argv)}") from exc

        for worker in threads:
            worker.join()

        result = CommandResult(
            args=final_argv,
            command_display=_quote_join(final_argv),
            exit_code=exit_code,
            stdout="".join(stdout_chunks),
            stderr="".join(stderr_chunks),
        )

    if check and not result.ok:
        raise CommandError(f"Command failed with exit code {result.exit_code}: {result.command_display}", result)
    return result


def terminate_process_group(proc: subprocess.Popen[str]) -> None:
    """
    Best-effort kill for a process group started with start_new_session=True.
    """
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
