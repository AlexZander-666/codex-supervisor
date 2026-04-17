# Codex Supervisor

Windows-first queueing and recovery supervisor for Codex CLI.

It provides a local daemon plus operator CLI for:

- `submit`
- `status`
- `list`
- `pause`
- `resume`
- `cancel`
- `logs`
- `start-daemon`

It also scans Codex session logs under `CODEX_HOME\sessions` and automatically enqueues `resume_session` work when it detects:

- `429 Too Many Requests`
- `stream disconnected before completion`

Recovered sessions are resumed with `codex exec resume`. New tasks are always submitted through the supervisor queue.

## Design Constraints

- Local CLI + daemon only
- No Web UI
- No takeover of the original Windows Terminal UI
- Supervisor state is stored only under this repo's `data/`
- Codex internal state under `C:\Users\black\.codex` is read-only input
- Default shared concurrency is `2`

## Install

```powershell
cd C:\Users\black\tools\codex-supervisor
pip install -e .[dev]
```

## Start The Daemon

```powershell
python -m codex_supervisor start-daemon
```

Expected runtime artifacts:

- `data/supervisor.db`
- `data/daemon.lock`
- `data/logs/task-<id>.jsonl`

## Operator Commands

Submit new work:

```powershell
codex-supervisor submit --cwd C:\Windows\system32 --prompt "inspect recent 429 errors"
```

Inspect queue state:

```powershell
codex-supervisor list
codex-supervisor status --task-id 1
codex-supervisor logs --task-id 1
```

Control a queued task:

```powershell
codex-supervisor pause --task-id 1
codex-supervisor resume --task-id 1
codex-supervisor cancel --task-id 1
```

## Recovery Workflow

1. Start the daemon once.
2. Submit all new work through `codex-supervisor submit`.
3. Leave existing interactive Codex sessions alone.
4. Let the daemon scan `CODEX_HOME\sessions`.
5. When a recoverable interruption is found, the daemon creates a `resume_session` task.
6. The task runs `codex exec resume --json --skip-git-repo-check <session-id> <prompt>`.
7. If the resumed task hits a recoverable interruption again, the daemon backs off and retries automatically.

## Runtime Notes

- `data/` is runtime-only and should not be committed.
- A session that contains a recoverable error but later reaches `task_complete` is not re-enqueued.
- On Windows, the daemon resolves the Codex executable through `PATH` or `%APPDATA%\npm\codex.cmd` so background launches work consistently.

## Development

Run tests:

```powershell
python -m pytest tests -q
```

## Included Skills

This repository also includes reusable operator skills under `skills/`:

- `operating-codex-supervisor`
- `publishing-codex-supervisor-project`

These capture the best practices for:

- daemonized Codex work recovery
- queue operations and monitoring
- failure diagnosis
- packaging and publishing the project to GitHub
