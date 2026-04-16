from pathlib import Path

from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.scheduler import Scheduler
from codex_supervisor.state import StateStore


def test_scheduler_only_selects_two_ready_tasks(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "supervisor.db")
    for index in range(3):
        store.create_task(
            kind=TaskKind.EXEC_PROMPT,
            cwd=rf"C:\job-{index}",
            payload={"prompt": f"job {index}"},
            priority=50,
        )
    scheduler = Scheduler(store=store, max_concurrency=2, lease_owner="daemon-a")
    ready = scheduler.claim_ready_tasks()
    assert len(ready) == 2
    claimed_statuses = [store.get_task(task.id).status for task in ready]
    assert claimed_statuses == [TaskStatus.LAUNCHING, TaskStatus.LAUNCHING]
