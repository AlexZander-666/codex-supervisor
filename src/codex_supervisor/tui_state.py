from dataclasses import dataclass
import json
from pathlib import Path

from codex_supervisor.models import TaskRecord


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: int
    status: str
    stage: str
    current_command: str
    recent_output: str
    retry_count: int


def build_task_snapshot(task: TaskRecord, log_path: Path) -> TaskSnapshot:
    stage = "idle"
    current_command = ""
    recent_output = ""

    if log_path.exists():
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            item = data.get("item", {})
            if data.get("type") == "item.started" and item.get("type") == "command_execution":
                stage = "command_execution"
                current_command = item.get("command", "")
            if data.get("type") == "item.completed" and item.get("type") == "agent_message":
                recent_output = item.get("text", "")

    return TaskSnapshot(
        task_id=task.id,
        status=task.status.value,
        stage=stage,
        current_command=current_command,
        recent_output=recent_output,
        retry_count=task.attempt_count,
    )
