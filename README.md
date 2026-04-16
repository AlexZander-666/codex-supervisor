# Codex Supervisor

Queueing and recovery supervisor for Codex CLI on Windows.

## Start the daemon

```powershell
python -m codex_supervisor start-daemon
```

## Submit a task

```powershell
codex-supervisor submit --cwd C:\Windows\system32 --prompt "inspect recent 429 errors"
```

## Inspect queue state

```powershell
codex-supervisor list
codex-supervisor status --task-id 1
codex-supervisor logs --task-id 1
```

## Operator workflow

1. Start `python -m codex_supervisor start-daemon` once.
2. Submit new work through `codex-supervisor submit`.
3. Use `codex-supervisor list` and `status` to inspect queue health.
4. Use `codex-supervisor logs --task-id N` to inspect a failing task.
5. Leave existing interactive Codex sessions alone; the supervisor will create `resume_session` recovery tasks when their JSONL logs show `429 Too Many Requests` or `stream disconnected before completion`.
