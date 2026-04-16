from pathlib import Path
import subprocess

from codex_supervisor.config import SupervisorConfig
from codex_supervisor.models import TaskKind


def build_codex_command(
    *,
    config: SupervisorConfig,
    task_kind: TaskKind,
    cwd: str,
    payload: dict,
) -> list[str]:
    if task_kind is TaskKind.EXEC_PROMPT:
        return [
            config.codex_bin,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "-C",
            cwd,
            payload["prompt"],
        ]
    return [
        config.codex_bin,
        "exec",
        "resume",
        "--json",
        payload["session_id"],
        payload["prompt"],
    ]


def launch_task(
    *,
    config: SupervisorConfig,
    task_kind: TaskKind,
    cwd: str,
    payload: dict,
    log_path: Path,
) -> subprocess.Popen:
    command = build_codex_command(
        config=config,
        task_kind=task_kind,
        cwd=cwd,
        payload=payload,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
