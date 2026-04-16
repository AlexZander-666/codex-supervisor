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
