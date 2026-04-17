from pathlib import Path
import json
import os
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
    fake_script = os.environ.get("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT")
    if fake_script:
        if task_kind is TaskKind.EXEC_PROMPT:
            return [config.codex_bin, fake_script, "exec", payload["prompt"]]
        return [
            config.codex_bin,
            fake_script,
            "resume",
            payload["session_id"],
            payload["prompt"],
        ]

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
        "--skip-git-repo-check",
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
    handle.write(
        json.dumps(
            {
                "source": "supervisor",
                "type": "launch",
                "task_kind": task_kind.value,
                "cwd": cwd,
                "command": command,
            },
            separators=(",", ":"),
        )
        + "\n"
    )
    handle.flush()
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
