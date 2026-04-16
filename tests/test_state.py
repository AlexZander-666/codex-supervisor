from pathlib import Path

from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore


def test_state_store_persists_and_transitions_tasks(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=r"C:\Windows\system32",
        payload={"prompt": "echo hello"},
        priority=50,
    )
    queued = store.get_task(task_id)
    assert queued.status is TaskStatus.QUEUED

    store.transition_task(task_id, TaskStatus.RUNNING, lease_owner="daemon-1")
    running = store.get_task(task_id)
    assert running.status is TaskStatus.RUNNING
    assert running.lease_owner == "daemon-1"
