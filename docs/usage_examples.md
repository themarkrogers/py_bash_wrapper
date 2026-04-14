# Usage examples

Copy-paste patterns for the public API in `py_bash_wrapper.bash_utils`. Signatures and edge cases are fully documented
in the source docstrings; this page focuses on **safe defaults** and common flows.

## Install from PyPI

```bash
pip install py_bash_wrapper
```

```python
from py_bash_wrapper.bash_utils import run_command

print(run_command(["echo", "hello"], check=True).stdout)
```

For a development checkout, see [README.md](../README.md) (Initial setup).

## Prefer `run_command` (no shell)

`run_command` accepts either a **`Sequence[str]`** (argv) or a **`str`**. A string is split with **`shlex.split`** into
argv and still runs **without** a shell -- there are no pipes, redirects, globbing, or other shell features. Use
**`run_bash`** when you need those.

Prefer a list when arguments are dynamic but individually controlled: each element is one argument, so there is no
parsing ambiguity. A string is convenient for literals (e.g., quoted segments) but is not a substitute for Bash; do not
pass untrusted strings expecting them to be "just argv" without reviewing how `shlex.split` will tokenize them (still
validate inputs in your own code).

```python
from py_bash_wrapper.bash_utils import run_command

result = run_command(["echo", "hello"], check=True)
print(result.stdout)

# Equivalent argv after shlex.split; still no shell.
result = run_command('echo "hello world"', check=True)
print(result.stdout)
```

## Use `run_bash` only when you need shell features

`run_bash` runs the string through Bash (`bash -c`, with optional `set -euo pipefail` when `strict=True`). **Do not**
pass untrusted or externally controlled strings as `command`.

```python
from py_bash_wrapper.bash_utils import run_bash

result = run_bash("echo hello | wc -c", check=True)
print(result.stdout.strip())
```

`CommandResult.command_display` is the original Bash source for `run_bash`, while `args` reflects the actual argv passed
to the process (e.g., `bash`, `-c`, script).

## Errors: `check=True` and `CommandError`

With `check=True`, a non-zero exit code raises `CommandError` and attaches the `CommandResult` on `exc.result`.

```python
from py_bash_wrapper.bash_utils import CommandError, run_command

try:
    run_command(["false"], check=True)
except CommandError as exc:
    print(exc.result.exit_code)
```

## Post-checking output: `check_result_for_text` and `require_success`

Some tools exit 0 but print failure markers. Use `check_result_for_text` for substring checks, or
`require_success` to assert a zero exit code on an existing `CommandResult`.

```python
from py_bash_wrapper.bash_utils import check_result_for_text, require_success, run_command

result = run_command(["some-tool", "--json"], check=False)
require_success(result)
check_result_for_text(result, error_substrings=["FATAL", "ERROR:"])
```

## Unix `user` parameter

`run_command` and `run_bash` accept `user="someunixuser"` on **POSIX** only:

- If the current effective UID **matches** that user (per the passwd database), the command runs **directly** -- no
  `sudo`, no `preexec_fn` -- so the merged environment you pass in (including `PATH`) is what the child sees.
- If the effective UID is **0** (root) and the target user is **different**, the child drops privileges via
  `preexec_fn`.
- Otherwise (non-root, different user), the code prepends **`sudo -H -u user --`** when `sudo` is on `PATH`; if `sudo`
  is missing, it raises `RuntimeError`. Unknown usernames raise `ValueError`.

When `sudo` is involved, many systems configure **`secure_path`**, so the child may still see a reduced `PATH` even if
your Python-side env included extra directories. Mitigations include using full paths to binaries, adjusting sudoers
for your environment, or relying on the same-user shortcut above when the process already runs as that account.

This is best-effort and depends on OS permissions and sudo policy; it is not a security boundary by itself.

## Imports and version

```python
import py_bash_wrapper
from py_bash_wrapper.bash_utils import CommandResult, run_bash, run_command

print(py_bash_wrapper.__version__)
```

For contributor setup (virtualenv, lint, tests), see [README.md](../README.md) and [code_style.md](code_style.md).
