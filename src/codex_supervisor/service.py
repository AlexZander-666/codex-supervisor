import os
from pathlib import Path

from codex_supervisor.config import load_config
from codex_supervisor.ipc import CommandInbox
from codex_supervisor.models import TaskKind
from codex_supervisor.state import StateStore
from codex_supervisor.tui_state import TaskSnapshot, load_task_snapshots


def resolve_project_root() -> Path:
    root = os.environ.get("CODEX_SUPERVISOR_PROJECT_ROOT")
    if root:
        return Path(root)
    return Path(r"C:\Users\black\tools\codex-supervisor")


def submit_exec_task(*, cwd: str, prompt: str, priority: int) -> None:
    config = load_config(resolve_project_root())
    inbox = CommandInbox(config.data_dir / "commands")
    inbox.write_command(
        {
            "type": "submit",
            "kind": TaskKind.EXEC_PROMPT.value,
            "cwd": cwd,
            "payload": {"prompt": prompt},
            "priority": priority,
        }
    )


def write_operator_command(*, command_type: str, task_id: int) -> None:
    config = load_config(resolve_project_root())
    inbox = CommandInbox(config.data_dir / "commands")
    inbox.write_command({"type": command_type, "task_id": task_id})


def read_task_snapshots() -> list[TaskSnapshot]:
    config = load_config(resolve_project_root())
    store = StateStore(config.data_dir / "supervisor.db")
    return load_task_snapshots(store, config.data_dir)


def render_task_status(task_id: int) -> str:
    config = load_config(resolve_project_root())
    store = StateStore(config.data_dir / "supervisor.db")
    task = store.get_task(task_id)
    return (
        f"task_id={task.id} status={task.status.value} "
        f"kind={task.kind.value} attempts={task.attempt_count}"
    )


def render_task_list() -> str:
    config = load_config(resolve_project_root())
    store = StateStore(config.data_dir / "supervisor.db")
    tasks = store.list_tasks(limit=50)
    return "\n".join(
        (
            f"task_id={task.id} status={task.status.value} "
            f"kind={task.kind.value} attempts={task.attempt_count}"
        )
        for task in tasks
    )


def read_task_logs(task_id: int) -> str:
    config = load_config(resolve_project_root())
    log_path = config.data_dir / "logs" / f"task-{task_id}.jsonl"
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")
