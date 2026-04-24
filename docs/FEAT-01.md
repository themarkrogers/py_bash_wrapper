# FEAT-01: Streaming process output and file-object stdio passthrough

## Problem statement

Today `run_command` and `run_bash` call `subprocess.run(..., capture_output=True)`, so output is only available after
process exit. This blocks real-time observability for long-running commands.

One important use case is running long Bash operations that print logs steadily over time. When output is buffered in
memory and written to disk only at the end, downstream timestamps can look misleading compared to when events occurred.

## Feature goals

- Allow callers to stream child stdout/stderr line-by-line while the process runs.
- Allow callers to pass open file objects directly as `stdout`/`stderr` sinks for the child.
- Keep current default behavior unchanged (collect output and return `CommandResult`).
- Preserve existing error behavior (`check=True`, `CommandError`, `TimeoutError`) as closely as possible.

## Non-goals

- No async API in this iteration.
- No background process manager in this iteration.
- No change to existing result fields in `CommandResult` for the default capture path.

## Proposed API changes

Apply the same new kwargs to `run_command` and `run_bash`:

- `stdout`: supports `None`, `subprocess.PIPE` (default behavior via capture), file-like object, or `subprocess.STDOUT`.
- `stderr`: supports `None`, `subprocess.PIPE` (default behavior via capture), file-like object, or `subprocess.STDOUT`.
- `stream_callback`: optional callback for incremental log events.

Suggested callback shape:

```python
Callable[[str, str], None]
```

Where arguments are `(stream_name, chunk_or_line)`, and `stream_name` is `"stdout"` or `"stderr"`.

Compatibility rule:

- If caller passes explicit `stdout`/`stderr` file objects, that routing wins and `stream_callback` for that stream is
  disabled unless we intentionally implement tee semantics.

## File-by-file implementation plan

### 1) `py_bash_wrapper/bash_utils.py`

Primary implementation work happens here.

Changes:

- **`run_command` signature/docstring**
  - Add new kwargs for stdio routing and streaming callback.
  - Document interactions with `text`, `timeout`, and `check`.
- **Execution path split**
  - Keep current `subprocess.run` path for the default capture case to minimize risk.
  - Add a new `subprocess.Popen` path when streaming callback and/or custom stdio file objects are provided.
- **`Popen` streaming implementation**
  - Use `stdout=PIPE` / `stderr=PIPE` when we need to consume stream data in Python.
  - Read from streams incrementally and call `stream_callback` as lines/chunks arrive.
  - Accumulate captured output only for streams that are still configured for capture.
  - Respect timeout: on timeout, terminate process group (best effort), then raise `TimeoutError`.
- **File-object passthrough**
  - If caller passes open file handles for `stdout` or `stderr`, forward directly to `Popen`.
  - Do not duplicate writes in Python unless tee mode is added later.
- **Result assembly**
  - Return `CommandResult` with `stdout`/`stderr` as captured strings (empty when not captured).
  - Keep `command_display` behavior unchanged.
- **`run_bash` pass-through**
  - Thread new kwargs through to `run_command`.
  - Keep `run_bash` user-facing `command_display` override behavior.

Potential helper additions in this same file:

- `_normalize_stdio_targets(...)`
- `_run_command_via_popen(...)`
- `_iter_stream_lines(...)` (or chunk-based iterator)

### 2) `test/test_bash_utils.py`

Extend existing unit tests (currently focused on mocked `subprocess.run`) with new coverage for streaming and stdio
passthrough behavior.

Add tests for:

- `run_command` default path remains `subprocess.run` with capture semantics.
- `run_command` streaming path uses `subprocess.Popen`.
- Callback receives stdout/stderr data incrementally and in expected stream labels.
- Passing file-like objects for `stdout` and/or `stderr` routes output to those objects.
- `stderr=subprocess.STDOUT` behavior remains valid in streaming mode.
- Timeout behavior in `Popen` path raises `TimeoutError` and performs cleanup.
- `check=True` still raises `CommandError` in `Popen` path with attached result.

### 3) `test/test_bash_utils_smoke.py`

Add or update integration-style smoke tests with real subprocesses to verify end-to-end behavior:

- Long-running command emits multiple lines with delays; callback sees multiple events before process exit.
- File sink receives output while process runs (not just post-process write by caller logic).

This file is the right place to assert practical "streaming works in real execution" behavior that mocks can miss.

### 4) `docs/usage_examples.md`

Add user-facing examples for:

- Streaming to a callback for progress logs.
- Sending child output directly to an open log file.
- Combined pattern: file-object routing and callback limitations/expectations.

Also clarify when to use default capture vs streaming mode.

### 5) `README.md` (if command API is documented there)

If `README.md` contains API snippets for `run_command` / `run_bash`, update examples to mention streaming and file
object support so PyPI and GitHub readers see the new capability quickly.

## Behavior details and decisions to lock before coding

- **Streaming unit**: line-based (`readline`) vs chunk-based (`read`) callbacks.
  - Recommendation: line-based first for log-oriented use cases.
- **Tee semantics**: whether callback should still fire when stream is routed to file object.
  - Recommendation: no tee in FEAT-01 to keep behavior simple and predictable.
- **Text vs bytes**
  - Current API is text-first; keep that default and document callback payload type as `str`.
- **Ordering guarantees**
  - Callback ordering should be per-stream, not globally total-ordered across stdout/stderr.

## Rollout and validation checklist

- Implement `bash_utils.py` changes behind clear conditional pathing.
- Add/adjust unit tests in `test/test_bash_utils.py`.
- Add smoke coverage in `test/test_bash_utils_smoke.py`.
- Update docs (`docs/usage_examples.md`, optionally `README.md`).
- Run test suite and confirm no regressions in existing behavior.
