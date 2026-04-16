import os
from pathlib import Path
import time

from codex_supervisor.config import SupervisorConfig, load_config
from codex_supervisor.ipc import CommandInbox
from codex_supervisor.log_parser import classify_session_file
from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.runner import launch_task
from codex_supervisor.scheduler import Scheduler
from codex_supervisor.service import resolve_project_root
from codex_supervisor.state import StateStore


def acquire_daemon_lock(lock_path: Path) -> Path | None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))

    return lock_path


def compute_retry_delay_seconds(reason: str, attempt_count: int) -> int:
    if reason == "http_429":
        return min(600, 30 * (2 ** max(0, attempt_count - 1)))
    if reason == "stream_disconnect":
        return min(180, 15 * max(1, attempt_count))
    return 60


def run_single_daemon_iteration(config: SupervisorConfig) -> None:
    store = StateStore(config.data_dir / "supervisor.db")
    scheduler = Scheduler(
        store=store,
        max_concurrency=config.max_concurrency,
        lease_owner="daemon-main",
    )
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
        process = launch_task(
            config=config,
            task_kind=task.kind,
            cwd=task.cwd,
            payload=task.payload,
            log_path=log_path,
        )
        exit_code = process.wait(timeout=1200)
        finding = classify_session_file(log_path)
        if exit_code == 0 and finding is None:
            store.transition_task(task.id, TaskStatus.SUCCEEDED, lease_owner=None)
            continue
        reason = finding.reason if finding is not None else "child_exit"
        delay = compute_retry_delay_seconds(reason, task.attempt_count + 1)
        store.increment_attempt_count(task.id)
        scheduler.mark_backoff(task.id, delay)


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
