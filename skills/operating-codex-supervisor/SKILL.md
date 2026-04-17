---
name: operating-codex-supervisor
description: Use when operating a local Codex Supervisor daemon on Windows to queue work, resume interrupted Codex sessions, inspect queue state, or recover from 429 and stream disconnect failures.
---

# Operating Codex Supervisor

## Overview

Use the supervisor as the only control plane for queued Codex work and session recovery.
Keep Codex internal state read-only under `CODEX_HOME`; keep all supervisor-owned state under the project's `data/` directory.

## When to Use

- A Windows host needs a persistent local queue for Codex CLI work.
- Existing Codex session logs must be scanned for `429 Too Many Requests` or `stream disconnected before completion`.
- Interrupted work must be resumed through `codex exec resume`.
- You need deterministic operator commands: `submit`, `status`, `list`, `pause`, `resume`, `cancel`, `logs`, `start-daemon`.

## Preconditions

- Start from the project root.
- Use the real Codex home via `CODEX_HOME`, but do not write into it.
- Install the package in editable mode if the CLI entry point is not yet available:

```powershell
pip install -e .
```

## Bootstrap

```powershell
python -m codex_supervisor start-daemon
```

Expect:
- A daemon lock under `data/daemon.lock`
- A SQLite state DB under `data/supervisor.db`
- Per-task logs under `data/logs/`

## Submit And Control Work

```powershell
codex-supervisor submit --cwd C:\path\to\repo --prompt "do the task"
codex-supervisor list
codex-supervisor status --task-id 1
codex-supervisor pause --task-id 1
codex-supervisor resume --task-id 1
codex-supervisor cancel --task-id 1
codex-supervisor logs --task-id 1
```

## Terminal TUI

```powershell
codex-supervisor tui
```

Use the TUI when you need a structured live console for supervisor-managed tasks only.

What it shows:
- Task status
- Current stage
- Current command
- Retry count
- Latest error
- Recent output tail

Default keys:
- `j` / `k` to move between tasks
- `enter` to keep the current task focused
- `p` to pause
- `r` to resume
- `c` to cancel
- `l` to keep recent output visible
- `q` to quit

Operator actions still enqueue JSON commands into `data/commands`; the daemon remains the only execution engine.

## Recovery Rules

- New work must be submitted through the supervisor queue.
- Resumed work must use `resume_session` tasks that execute `codex exec resume`.
- Recovery triggers are only:
  - `429 Too Many Requests`
  - `stream disconnected before completion`
- A session that later reaches `task_complete` must not be re-enqueued.
- Shared concurrency default stays `2`.

## Monitoring Pattern

1. Confirm daemon is running and lock file exists.
2. Open `codex-supervisor tui` for the structured live view, or use `codex-supervisor list` if a plain CLI view is enough.
3. Inspect `codex-supervisor logs --task-id <id>` when raw task JSONL is needed.
4. If a task hits a recoverable interruption, allow the daemon to back off and retry.
5. Only intervene manually after root cause evidence is collected.

## Failure Diagnosis

- `launching` with empty task log:
  Check daemon stderr first. On Windows this usually means Codex executable resolution failed.
- `Not inside a trusted directory`:
  Ensure resume commands include `--skip-git-repo-check`.
- Repeated recovery of an already-finished session:
  Verify the classifier ignores recoverable errors that are followed by `task_complete`.
- `backing_off`:
  This is expected after recoverable interruptions. Confirm the attempt count increments and the daemon stays alive.

## Completion Checklist

- `codex-supervisor list` shows the intended tasks in `succeeded`.
- Fresh tests pass for the supervisor project.
- Runtime artifacts remain under `data/` only.

