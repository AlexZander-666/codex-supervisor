from dataclasses import dataclass
from datetime import datetime, timezone

from codex_supervisor.models import TaskRecord, TaskStatus
from codex_supervisor.state import StateStore


@dataclass
class Scheduler:
    store: StateStore
    max_concurrency: int
    lease_owner: str

    def claim_ready_tasks(self) -> list[TaskRecord]:
        running_count = self.store.count_active_tasks()
        available_slots = max(0, self.max_concurrency - running_count)
        if available_slots == 0:
            return []
        ready = self.store.list_ready_tasks(limit=available_slots)
        claimed: list[TaskRecord] = []
        for task in ready:
            self.store.transition_task(
                task.id,
                TaskStatus.LAUNCHING,
                lease_owner=self.lease_owner,
            )
            claimed.append(self.store.get_task(task.id))
        return claimed

    def mark_backoff(self, task_id: int, seconds: int) -> None:
        run_at = datetime.now(timezone.utc).timestamp() + seconds
        self.store.set_backoff(task_id, run_at)
