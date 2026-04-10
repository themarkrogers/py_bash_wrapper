# Usage examples

Copy-paste patterns for the public API in `py_bash.bash_utils`. Signatures and edge cases are fully documented in the
source docstrings; this page focuses on **safe defaults** and common flows.

## Install from PyPI

```bash
pip install py_bash
```

```python
from py_bash.bash_utils import run_command

print(run_command(["echo", "hello"], check=True).stdout)
```

For a development checkout, see [README.md](../README.md) (Initial setup).

## Prefer `run_command` (no shell)

Use a fixed argument list when you do not need pipes, redirects, globbing, or other shell syntax. This avoids shell
injection when arguments are dynamic but individually controlled (still validate inputs in your own code).

```python
from py_bash.bash_utils import run_command

result = run_command(["echo", "hello"], check=True)
print(result.stdout)
```

## Use `run_bash` only when you need shell features

`run_bash` runs the string through Bash (`bash -c`, with optional `set -euo pipefail` when `strict=True`). **Do not**
pass untrusted or externally controlled strings as `command`.

```python
from py_bash.bash_utils import run_bash

result = run_bash("echo hello | wc -c", check=True)
print(result.stdout.strip())
```

`CommandResult.command_display` is the original Bash source for `run_bash`, while `args` reflects the actual argv passed
to the process (e.g., `bash`, `-c`, script).

## Errors: `check=True` and `CommandError`

With `check=True`, a non-zero exit code raises `CommandError` and attaches the `CommandResult` on `exc.result`.

```python
from py_bash.bash_utils import CommandError, run_command

try:
    run_command(["false"], check=True)
except CommandError as exc:
    print(exc.result.exit_code)
```

## Post-checking output: `check_result_for_text` and `require_success`

Some tools exit 0 but print failure markers. Use `check_result_for_text` for substring checks, or
`require_success` to assert a zero exit code on an existing `CommandResult`.

```python
from py_bash.bash_utils import check_result_for_text, require_success, run_command

result = run_command(["some-tool", "--json"], check=False)
require_success(result)
check_result_for_text(result, error_substrings=["FATAL", "ERROR:"])
```

## Unix `user` parameter

`run_command` and `run_bash` accept `user="someunixuser"` on **POSIX** only:

- If the current effective UID is **0** (root), the child drops privileges via `preexec_fn`.
- Otherwise, the code prepends **`sudo -H -u user --`** when `sudo` is on `PATH`; if not root and no `sudo`, it raises
  `RuntimeError`.

This is best-effort and depends on OS permissions and sudo policy; it is not a security boundary by itself.

## Imports and version

```python
import py_bash
from py_bash.bash_utils import CommandResult, run_bash, run_command

print(py_bash.__version__)
```

For contributor setup (virtualenv, lint, tests), see [README.md](../README.md) and [code_style.md](code_style.md).
