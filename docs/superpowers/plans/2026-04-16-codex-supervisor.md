# Codex Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-native Codex supervisor that accepts new queued jobs, enforces a shared concurrency limit of `2`, detects interrupted existing Codex sessions, and resumes them with backoff by calling `codex exec` and `codex exec resume`.

**Architecture:** A single Python daemon owns the queue, the active slot count, retry policy, and session scanning. A thin local CLI writes command envelopes into a filesystem inbox and reads SQLite-backed state from the daemon. The daemon launches Codex as child processes, persists task state in SQLite, and monitors `C:\Users\black\.codex\sessions` for `429` and disconnect failures that should be re-queued as recovery work.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `sqlite3`, `subprocess`, `threading`, `pathlib`, `json`, `logging`), `pytest` for tests

---

## File Structure

**Project root:** `C:\Users\black\tools\codex-supervisor`

**Create these files and directories:**

- `C:\Users\black\tools\codex-supervisor\.gitignore`
- `C:\Users\black\tools\codex-supervisor\pyproject.toml`
- `C:\Users\black\tools\codex-supervisor\README.md`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\__init__.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\__main__.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\cli.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\config.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\models.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\state.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\ipc.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\daemon.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\scheduler.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\runner.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\session_monitor.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\log_parser.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\paths.py`
- `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\service.py`
- `C:\Users\black\tools\codex-supervisor\data\commands\`
- `C:\Users\black\tools\codex-supervisor\data\logs\`
- `C:\Users\black\tools\codex-supervisor\tests\conftest.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_cli.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_state.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_ipc.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_scheduler.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_runner.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_session_monitor.py`
- `C:\Users\black\tools\codex-supervisor\tests\test_e2e.py`
- `C:\Users\black\tools\codex-supervisor\tests\fixtures\session_error_429.jsonl`
- `C:\Users\black\tools\codex-supervisor\tests\fixtures\session_error_disconnect.jsonl`
- `C:\Users\black\tools\codex-supervisor\tests\fixtures\session_success_after_retry.jsonl`
- `C:\Users\black\tools\codex-supervisor\tests\fake_codex.py`

**Responsibilities:**

- `config.py`: Default config values and environment overrides.
- `models.py`: Dataclasses and enums for tasks, commands, attempts, and monitor findings.
- `state.py`: SQLite schema and repository operations.
- `ipc.py`: Filesystem inbox writer/reader for CLI-to-daemon commands.
- `daemon.py`: Single-instance daemon lifecycle and worker loop orchestration.
- `scheduler.py`: Slot allocation, task selection, backoff decisions, and task transitions.
- `runner.py`: Child process launch and completion handling for `codex exec` and `codex exec resume`.
- `session_monitor.py`: Poll and classify existing `.codex` sessions for recovery.
- `log_parser.py`: Parse Codex JSONL events and extract `429` and disconnect errors.
- `service.py`: High-level app wiring used by CLI and daemon.

### Task 1: Bootstrap the repository and CLI entrypoint

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\.gitignore`
- Create: `C:\Users\black\tools\codex-supervisor\pyproject.toml`
- Create: `C:\Users\black\tools\codex-supervisor\README.md`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\__init__.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\__main__.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\cli.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from codex_supervisor.cli import build_parser


def test_cli_has_expected_top_level_commands() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert set(choices) >= {
        "start-daemon",
        "submit",
        "status",
        "list",
        "pause",
        "resume",
        "cancel",
        "logs",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'codex_supervisor'`

- [ ] **Step 3: Create package metadata and CLI skeleton**

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "codex-supervisor"
version = "0.1.0"
description = "Queueing and recovery supervisor for Codex CLI on Windows"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
codex-supervisor = "codex_supervisor.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-supervisor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in [
        "start-daemon",
        "submit",
        "status",
        "list",
        "pause",
        "resume",
        "cancel",
        "logs",
    ]:
        subparsers.add_parser(name)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
```

```python
from codex_supervisor.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

```gitignore
__pycache__/
.pytest_cache/
.venv/
build/
dist/
data/*.db
data/*.lock
data/*.pid
data/logs/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Initialize git and commit**

Run: `git init`
Expected: `Initialized empty Git repository`

Run: `git add .`
Expected: no output

Run: `git commit -m "chore: bootstrap codex supervisor project"`
Expected: one root commit created

### Task 2: Define configuration, domain models, and SQLite state store

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\config.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\models.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\state.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\paths.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_state.py`

- [ ] **Step 1: Write the failing state transition test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL with `ImportError` for `StateStore` or `TaskKind`

- [ ] **Step 3: Implement config, models, paths, and SQLite schema**

```python
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class SupervisorConfig:
    project_root: Path
    data_dir: Path
    codex_home: Path
    max_concurrency: int = 2
    monitor_interval_seconds: int = 15
    scheduler_interval_seconds: int = 2
    retry_base_seconds: int = 30
    retry_cap_seconds: int = 600
    codex_bin: str = "codex"


def load_config(project_root: Path) -> SupervisorConfig:
    data_dir = project_root / "data"
    codex_home = Path(os.environ.get("CODEX_HOME", r"C:\Users\black\.codex"))
    codex_bin = os.environ.get("CODEX_SUPERVISOR_CODEX_BIN", "codex")
    return SupervisorConfig(
        project_root=project_root,
        data_dir=data_dir,
        codex_home=codex_home,
        codex_bin=codex_bin,
    )
```

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskKind(str, Enum):
    EXEC_PROMPT = "exec_prompt"
    RESUME_SESSION = "resume_session"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    LAUNCHING = "launching"
    RUNNING = "running"
    BACKING_OFF = "backing_off"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class TaskRecord:
    id: int
    kind: TaskKind
    status: TaskStatus
    cwd: str
    payload: dict[str, Any]
    priority: int
    lease_owner: str | None
    attempt_count: int
```

```python
import json
import sqlite3
from pathlib import Path

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

    def create_task(self, *, kind: TaskKind, cwd: str, payload: dict, priority: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (kind, status, cwd, payload_json, priority) VALUES (?, ?, ?, ?, ?)",
                (kind.value, TaskStatus.QUEUED.value, cwd, json.dumps(payload), priority),
            )
            return int(cursor.lastrowid)

    def get_task(self, task_id: int) -> TaskRecord:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, kind, status, cwd, payload_json, priority, lease_owner, attempt_count FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        assert row is not None
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

    def transition_task(self, task_id: int, status: TaskStatus, *, lease_owner: str | None = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, lease_owner = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, lease_owner, task_id),
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add pyproject.toml src tests`
Expected: no output

Run: `git commit -m "feat: add supervisor config and state store"`
Expected: one commit created

### Task 3: Implement filesystem IPC and daemon single-instance locking

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\ipc.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\daemon.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_ipc.py`

- [ ] **Step 1: Write failing IPC and lock tests**

```python
import json
from pathlib import Path

from codex_supervisor.daemon import acquire_daemon_lock
from codex_supervisor.ipc import CommandInbox


def test_command_inbox_round_trip(tmp_path: Path) -> None:
    inbox = CommandInbox(tmp_path / "commands")
    inbox.write_command({"type": "submit", "payload": {"prompt": "fix bug"}})
    files = list((tmp_path / "commands").glob("*.json"))
    assert len(files) == 1
    command = inbox.read_next_command()
    assert command["type"] == "submit"


def test_acquire_daemon_lock_is_single_owner(tmp_path: Path) -> None:
    lock_path = tmp_path / "daemon.lock"
    first = acquire_daemon_lock(lock_path)
    assert first is not None
    second = acquire_daemon_lock(lock_path)
    assert second is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ipc.py -v`
Expected: FAIL with `ImportError` for `CommandInbox`

- [ ] **Step 3: Implement command inbox and daemon lock**

```python
import json
import uuid
from pathlib import Path


class CommandInbox:
    def __init__(self, inbox_dir: Path) -> None:
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def write_command(self, command: dict) -> Path:
        temp_path = self.inbox_dir / f".{uuid.uuid4().hex}.tmp"
        final_path = self.inbox_dir / f"{uuid.uuid4().hex}.json"
        temp_path.write_text(json.dumps(command), encoding="utf-8")
        temp_path.replace(final_path)
        return final_path

    def read_next_command(self) -> dict | None:
        files = sorted(self.inbox_dir.glob("*.json"))
        if not files:
            return None
        path = files[0]
        data = json.loads(path.read_text(encoding="utf-8"))
        path.unlink()
        return data
```

```python
import os
from pathlib import Path


def acquire_daemon_lock(lock_path: Path) -> Path | None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return lock_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ipc.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add daemon lock and filesystem ipc"`
Expected: one commit created

### Task 4: Expand the CLI into a real control surface

**Files:**
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\cli.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\service.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_cli.py`

- [ ] **Step 1: Write failing CLI behavior tests**

```python
from pathlib import Path

from codex_supervisor.cli import main


def test_submit_writes_command_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    exit_code = main(
        [
            "submit",
            "--cwd",
            r"C:\Windows\system32",
            "--prompt",
            "inspect latest 429 events",
        ]
    )
    assert exit_code == 0
    files = list((tmp_path / "data" / "commands").glob("*.json"))
    assert len(files) == 1


def test_status_reads_task_row(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    from codex_supervisor.state import StateStore
    from codex_supervisor.models import TaskKind

    store = StateStore(tmp_path / "data" / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=r"C:\Windows\system32",
        payload={"prompt": "hello"},
        priority=50,
    )
    exit_code = main(["status", "--task-id", str(task_id)])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"task_id={task_id}" in output


def test_list_prints_existing_tasks(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    from codex_supervisor.state import StateStore
    from codex_supervisor.models import TaskKind

    store = StateStore(tmp_path / "data" / "supervisor.db")
    store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=r"C:\Windows\system32",
        payload={"prompt": "hello"},
        priority=50,
    )
    exit_code = main(["list"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "status=queued" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL because `submit` and `status` do not yet implement behavior

- [ ] **Step 3: Implement CLI commands and service helpers**

```python
from pathlib import Path
import os

from codex_supervisor.config import load_config
from codex_supervisor.ipc import CommandInbox
from codex_supervisor.models import TaskKind
from codex_supervisor.state import StateStore


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


def render_task_status(task_id: int) -> str:
    config = load_config(resolve_project_root())
    store = StateStore(config.data_dir / "supervisor.db")
    task = store.get_task(task_id)
    return f"task_id={task.id} status={task.status.value} kind={task.kind.value} attempts={task.attempt_count}"


def render_task_list() -> str:
    config = load_config(resolve_project_root())
    store = StateStore(config.data_dir / "supervisor.db")
    tasks = store.list_tasks(limit=50)
    return "\n".join(
        f"task_id={task.id} status={task.status.value} kind={task.kind.value} attempts={task.attempt_count}"
        for task in tasks
    )
```

```python
submit = subparsers.add_parser("submit")
submit.add_argument("--cwd", required=True)
submit.add_argument("--prompt", required=True)
submit.add_argument("--priority", type=int, default=50)

status = subparsers.add_parser("status")
status.add_argument("--task-id", type=int, required=True)

subparsers.add_parser("list")

subparsers.add_parser("start-daemon")

if args.command == "submit":
    submit_exec_task(cwd=args.cwd, prompt=args.prompt, priority=args.priority)
    print("queued")
    return 0
if args.command == "status":
    print(render_task_status(args.task_id))
    return 0
if args.command == "list":
    print(render_task_list())
    return 0
if args.command == "start-daemon":
    from codex_supervisor.daemon import run_forever

    run_forever()
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add submit and status cli commands"`
Expected: one commit created

### Task 5: Build the scheduler and concurrency gate

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\scheduler.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\state.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_scheduler.py`

- [ ] **Step 1: Write failing scheduler tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scheduler.py -v`
Expected: FAIL because `Scheduler` does not exist

- [ ] **Step 3: Implement queue selection and slot enforcement**

```python
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
            self.store.transition_task(task.id, TaskStatus.LAUNCHING, lease_owner=self.lease_owner)
            claimed.append(self.store.get_task(task.id))
        return claimed

    def mark_backoff(self, task_id: int, seconds: int) -> None:
        run_at = datetime.now(timezone.utc).timestamp() + seconds
        self.store.set_backoff(task_id, run_at)
```

```python
def count_active_tasks(self) -> int:
    with sqlite3.connect(self.db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)",
            (TaskStatus.LAUNCHING.value, TaskStatus.RUNNING.value),
        ).fetchone()
    assert row is not None
    return int(row[0])


def list_ready_tasks(self, limit: int) -> list[TaskRecord]:
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


def list_tasks(self, limit: int) -> list[TaskRecord]:
    with sqlite3.connect(self.db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, kind, status, cwd, payload_json, priority, lease_owner, attempt_count
            FROM tasks
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
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
            "UPDATE tasks SET attempt_count = attempt_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add task scheduler and concurrency control"`
Expected: one commit created

### Task 6: Implement the Codex runner for `exec` and `exec resume`

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\runner.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\state.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_runner.py`
- Create: `C:\Users\black\tools\codex-supervisor\tests\fake_codex.py`

- [ ] **Step 1: Write failing runner tests with a fake Codex binary**

```python
from pathlib import Path

from codex_supervisor.config import SupervisorConfig
from codex_supervisor.models import TaskKind
from codex_supervisor.runner import build_codex_command


def test_build_codex_command_for_exec() -> None:
    config = SupervisorConfig(
        project_root=Path(r"C:\Users\black\tools\codex-supervisor"),
        data_dir=Path(r"C:\Users\black\tools\codex-supervisor\data"),
        codex_home=Path(r"C:\Users\black\.codex"),
        codex_bin="codex",
    )
    command = build_codex_command(
        config=config,
        task_kind=TaskKind.EXEC_PROMPT,
        cwd=r"C:\Windows\system32",
        payload={"prompt": "inspect rate limits"},
    )
    assert command[:4] == ["codex", "exec", "--json", "--skip-git-repo-check"]
    assert command[-1] == "inspect rate limits"


def test_build_codex_command_for_resume() -> None:
    config = SupervisorConfig(
        project_root=Path(r"C:\Users\black\tools\codex-supervisor"),
        data_dir=Path(r"C:\Users\black\tools\codex-supervisor\data"),
        codex_home=Path(r"C:\Users\black\.codex"),
        codex_bin="codex",
    )
    command = build_codex_command(
        config=config,
        task_kind=TaskKind.RESUME_SESSION,
        cwd=r"C:\Windows\system32",
        payload={"session_id": "abc-123", "prompt": "continue after 429"},
    )
    assert command[:4] == ["codex", "exec", "resume", "--json"]
    assert command[-2:] == ["abc-123", "continue after 429"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runner.py -v`
Expected: FAIL because `build_codex_command` does not exist

- [ ] **Step 3: Implement the runner and process launch contract**

```python
from pathlib import Path
import subprocess

from codex_supervisor.config import SupervisorConfig
from codex_supervisor.models import TaskKind


def build_codex_command(*, config: SupervisorConfig, task_kind: TaskKind, cwd: str, payload: dict) -> list[str]:
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


def launch_task(*, config: SupervisorConfig, task_kind: TaskKind, cwd: str, payload: dict, log_path: Path) -> subprocess.Popen:
    command = build_codex_command(config=config, task_kind=task_kind, cwd=cwd, payload=payload)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, text=True)
```

```python
import sys
import json


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:2] == ["exec", "--json"]:
        print(json.dumps({"event": "task_started", "prompt": args[-1]}))
        raise SystemExit(0)
    if args[:3] == ["exec", "resume", "--json"]:
        print(json.dumps({"event": "resumed", "session_id": args[-2]}))
        raise SystemExit(0)
    raise SystemExit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add codex process runner"`
Expected: one commit created

### Task 7: Parse Codex JSONL output and detect recovery-worthy failures

**Files:**
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\log_parser.py`
- Create: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\session_monitor.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_session_monitor.py`
- Create: `C:\Users\black\tools\codex-supervisor\tests\fixtures\session_error_429.jsonl`
- Create: `C:\Users\black\tools\codex-supervisor\tests\fixtures\session_error_disconnect.jsonl`

- [ ] **Step 1: Write failing parser tests**

```python
from pathlib import Path

from codex_supervisor.log_parser import classify_session_file


def test_classify_429_session(tmp_path: Path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-1","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"exceeded retry limit, last status: 429 Too Many Requests","codex_error_info":{"response_too_many_failed_attempts":{"http_status_code":429}}}}',
            ]
        ),
        encoding="utf-8",
    )
    finding = classify_session_file(session_file)
    assert finding.session_id == "s-1"
    assert finding.reason == "http_429"


def test_classify_disconnect_session(tmp_path: Path) -> None:
    session_file = tmp_path / "disconnect.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-2","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"stream disconnected before completion: stream closed before response.completed","codex_error_info":"other"}}',
            ]
        ),
        encoding="utf-8",
    )
    finding = classify_session_file(session_file)
    assert finding.session_id == "s-2"
    assert finding.reason == "stream_disconnect"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session_monitor.py -v`
Expected: FAIL because `classify_session_file` does not exist

- [ ] **Step 3: Implement parser and monitor dedupe rules**

```python
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class SessionFinding:
    session_id: str
    cwd: str
    reason: str
    message: str


def classify_session_file(session_path: Path) -> SessionFinding | None:
    session_id = ""
    cwd = ""
    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        data = json.loads(raw_line)
        if data["type"] == "session_meta":
            session_id = data["payload"]["id"]
            cwd = data["payload"]["cwd"]
        if data["type"] == "event_msg" and data["payload"]["type"] == "error":
            message = data["payload"]["message"]
            if "429 Too Many Requests" in message:
                return SessionFinding(session_id=session_id, cwd=cwd, reason="http_429", message=message)
            if "stream disconnected before completion" in message:
                return SessionFinding(session_id=session_id, cwd=cwd, reason="stream_disconnect", message=message)
    return None
```

```python
from pathlib import Path

from codex_supervisor.log_parser import SessionFinding, classify_session_file


class SessionMonitor:
    def __init__(self, sessions_root: Path) -> None:
        self.sessions_root = sessions_root
        self.seen_keys: set[tuple[str, str]] = set()

    def scan(self) -> list[SessionFinding]:
        findings: list[SessionFinding] = []
        for session_file in self.sessions_root.rglob("*.jsonl"):
            finding = classify_session_file(session_file)
            if finding is None:
                continue
            dedupe_key = (finding.session_id, finding.reason)
            if dedupe_key in self.seen_keys:
                continue
            self.seen_keys.add(dedupe_key)
            findings.append(finding)
        return findings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_session_monitor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add session log parser and recovery detector"`
Expected: one commit created

### Task 8: Wire the daemon loop, retry policy, and auto-resume behavior

**Files:**
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\daemon.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\scheduler.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\state.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\runner.py`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_e2e.py`

- [ ] **Step 1: Write the failing end-to-end queue and retry test**

```python
from pathlib import Path

from codex_supervisor.config import load_config
from codex_supervisor.daemon import run_single_daemon_iteration
from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore


def test_daemon_requeues_429_and_later_succeeds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    fake_codex = Path(__file__).parent / "fake_codex.py"
    monkeypatch.setenv("CODEX_SUPERVISOR_CODEX_BIN", "python")
    monkeypatch.setenv("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT", str(fake_codex))

    config = load_config(tmp_path)
    store = StateStore(config.data_dir / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "trigger 429 once"},
        priority=50,
    )

    run_single_daemon_iteration(config)
    first = store.get_task(task_id)
    assert first.status in {TaskStatus.BACKING_OFF, TaskStatus.RUNNING}

    store.force_ready(task_id)
    run_single_daemon_iteration(config)
    second = store.get_task(task_id)
    assert second.status is TaskStatus.SUCCEEDED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_e2e.py -v`
Expected: FAIL because the daemon loop does not launch or retry tasks yet

- [ ] **Step 3: Implement retry policy and daemon loop**

```python
def compute_retry_delay_seconds(reason: str, attempt_count: int) -> int:
    if reason == "http_429":
        return min(600, 30 * (2 ** max(0, attempt_count - 1)))
    if reason == "stream_disconnect":
        return min(180, 15 * max(1, attempt_count))
    return 60
```

```python
def run_single_daemon_iteration(config: SupervisorConfig) -> None:
    store = StateStore(config.data_dir / "supervisor.db")
    scheduler = Scheduler(store=store, max_concurrency=config.max_concurrency, lease_owner="daemon-main")
    inbox = CommandInbox(config.data_dir / "commands")
    command = inbox.read_next_command()
    while command is not None:
        if command["type"] == "submit":
            store.create_task(
                kind=TaskKind(command["kind"]),
                cwd=command["cwd"],
                payload=command["payload"],
                priority=command["priority"],
            )
        command = inbox.read_next_command()

    for task in scheduler.claim_ready_tasks():
        log_path = config.data_dir / "logs" / f"task-{task.id}.jsonl"
        process = launch_task(config=config, task_kind=task.kind, cwd=task.cwd, payload=task.payload, log_path=log_path)
        exit_code = process.wait(timeout=1200)
        finding = classify_session_file(log_path)
        if exit_code == 0 and finding is None:
            store.transition_task(task.id, TaskStatus.SUCCEEDED, lease_owner=None)
            continue
        reason = finding.reason if finding is not None else "child_exit"
        delay = compute_retry_delay_seconds(reason, task.attempt_count + 1)
        store.increment_attempt_count(task.id)
        scheduler.mark_backoff(task.id, delay)
```

```python
def run_forever() -> None:
    project_root = resolve_project_root()
    config = load_config(project_root)
    lock = acquire_daemon_lock(config.data_dir / "daemon.lock")
    if lock is None:
        raise SystemExit("daemon already running")
    print(f"daemon started max_concurrency={config.max_concurrency}")
    try:
        while True:
            run_single_daemon_iteration(config)
            time.sleep(config.scheduler_interval_seconds)
    finally:
        lock.unlink(missing_ok=True)
```

```python
if os.environ.get("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT"):
    script = os.environ["CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT"]
    if task_kind is TaskKind.EXEC_PROMPT:
        return [config.codex_bin, script, "exec", payload["prompt"]]
    return [config.codex_bin, script, "resume", payload["session_id"], payload["prompt"]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_e2e.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src tests`
Expected: no output

Run: `git commit -m "feat: add daemon loop and retry policy"`
Expected: one commit created

### Task 9: Add pause, cancel, logs, and operator documentation

**Files:**
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\cli.py`
- Modify: `C:\Users\black\tools\codex-supervisor\src\codex_supervisor\service.py`
- Modify: `C:\Users\black\tools\codex-supervisor\README.md`
- Test: `C:\Users\black\tools\codex-supervisor\tests\test_cli.py`

- [ ] **Step 1: Write failing operator command tests**

```python
from pathlib import Path

from codex_supervisor.cli import main
from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore


def test_pause_and_resume_write_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    store = StateStore(tmp_path / "data" / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "hello"},
        priority=50,
    )
    assert main(["pause", "--task-id", str(task_id)]) == 0
    assert main(["resume", "--task-id", str(task_id)]) == 0


def test_logs_reads_log_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    log_path = tmp_path / "data" / "logs" / "task-1.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('{"event":"hello"}\n', encoding="utf-8")
    assert main(["logs", "--task-id", "1"]) == 0
    assert '{"event":"hello"}' in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL because `pause`, `resume`, and `logs` are not implemented

- [ ] **Step 3: Implement operator commands and README**

```python
pause = subparsers.add_parser("pause")
pause.add_argument("--task-id", type=int, required=True)

resume = subparsers.add_parser("resume")
resume.add_argument("--task-id", type=int, required=True)

cancel = subparsers.add_parser("cancel")
cancel.add_argument("--task-id", type=int, required=True)

logs = subparsers.add_parser("logs")
logs.add_argument("--task-id", type=int, required=True)
```

```python
if args.command in {"pause", "resume", "cancel"}:
    inbox = CommandInbox(load_config(resolve_project_root()).data_dir / "commands")
    inbox.write_command({"type": args.command, "task_id": args.task_id})
    print(args.command)
    return 0
if args.command == "logs":
    config = load_config(resolve_project_root())
    log_path = config.data_dir / "logs" / f"task-{args.task_id}.jsonl"
    print(log_path.read_text(encoding="utf-8") if log_path.exists() else "")
    return 0
```

```markdown
# Codex Supervisor

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
```

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add README.md src tests`
Expected: no output

Run: `git commit -m "feat: finalize operator commands and docs"`
Expected: one commit created

### Task 10: Manual verification on the target Windows machine

**Files:**
- Modify: `C:\Users\black\tools\codex-supervisor\README.md`

- [ ] **Step 1: Install the package in editable mode**

Run: `python -m pip install -e .[dev]`
Expected: editable install completes without errors

- [ ] **Step 2: Start the daemon in one terminal**

Run: `python -m codex_supervisor start-daemon`
Expected: line containing `daemon started` and the configured concurrency limit `2`

- [ ] **Step 3: Submit three jobs and verify only two run immediately**

Run: `codex-supervisor submit --cwd C:\Windows\system32 --prompt "job one"`
Expected: `queued`

Run: `codex-supervisor submit --cwd C:\Windows\system32 --prompt "job two"`
Expected: `queued`

Run: `codex-supervisor submit --cwd C:\Windows\system32 --prompt "job three"`
Expected: `queued`

Run: `codex-supervisor list`
Expected: two tasks in `running` or `launching`, one task in `queued`

- [ ] **Step 4: Verify 429 recovery logic against a real interrupted session**

Run: `codex-supervisor list`
Expected: a recovery task appears with kind `resume_session` after a matching session monitor finding

Run: `codex-supervisor logs --task-id <recovery_task_id>`
Expected: JSONL log includes the resumed session id and later a success or backoff transition

- [ ] **Step 5: Record the exact operator workflow in the README**

```markdown
## Operator workflow

1. Start `python -m codex_supervisor start-daemon` once.
2. Submit new work through `codex-supervisor submit`.
3. Use `codex-supervisor list` and `status` to inspect queue health.
4. Use `codex-supervisor logs --task-id N` to inspect a failing task.
5. Leave existing interactive Codex sessions alone; the supervisor will create `resume_session` recovery tasks when their JSONL logs show `429 Too Many Requests` or `stream disconnected before completion`.
```
