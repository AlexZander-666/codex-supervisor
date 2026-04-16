import json
from pathlib import Path
import sqlite3

from codex_supervisor.models import TaskKind, TaskRecord, TaskStatus


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    cwd TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    priority INTEGER NOT NULL,
    lease_owner TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    def create_task(
        self,
        *,
        kind: TaskKind,
        cwd: str,
        payload: dict,
        priority: int,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                (
                    "INSERT INTO tasks (kind, status, cwd, payload_json, priority) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    kind.value,
                    TaskStatus.QUEUED.value,
                    cwd,
                    json.dumps(payload),
                    priority,
                ),
            )
            return int(cursor.lastrowid)

    def get_task(self, task_id: int) -> TaskRecord:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                (
                    "SELECT id, kind, status, cwd, payload_json, priority, lease_owner, "
                    "attempt_count FROM tasks WHERE id = ?"
                ),
                (task_id,),
            ).fetchone()
        assert row is not None
        return self._row_to_task(row)

    def transition_task(
        self,
        task_id: int,
        status: TaskStatus,
        *,
        lease_owner: str | None = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, lease_owner = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, lease_owner, task_id),
            )

    def list_tasks(self, *, limit: int = 50) -> list[TaskRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                (
                    "SELECT id, kind, status, cwd, payload_json, priority, lease_owner, "
                    "attempt_count FROM tasks ORDER BY id ASC LIMIT ?"
                ),
                (limit,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def count_active_tasks(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.LAUNCHING.value, TaskStatus.RUNNING.value),
            ).fetchone()
        assert row is not None
        return int(row[0])

    def list_ready_tasks(self, *, limit: int) -> list[TaskRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, kind, status, cwd, payload_json, priority, lease_owner, attempt_count
                FROM tasks
                WHERE status = ?
                ORDER BY priority DESC, id ASC
                LIMIT ?
                """,
                (TaskStatus.QUEUED.value, limit),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def set_backoff(self, task_id: int, run_at_epoch: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, next_run_at = ?, lease_owner = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (TaskStatus.BACKING_OFF.value, str(run_at_epoch), task_id),
            )

    def increment_attempt_count(self, task_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                (
                    "UPDATE tasks SET attempt_count = attempt_count + 1, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                ),
                (task_id,),
            )

    def force_ready(self, task_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, next_run_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (TaskStatus.QUEUED.value, task_id),
            )

    def _row_to_task(self, row: tuple) -> TaskRecord:
        return TaskRecord(
            id=row[0],
            kind=TaskKind(row[1]),
            status=TaskStatus(row[2]),
            cwd=row[3],
            payload=json.loads(row[4]),
            priority=row[5],
            lease_owner=row[6],
            attempt_count=row[7],
        )
