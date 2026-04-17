from pathlib import Path

from codex_supervisor.config import load_config
from codex_supervisor.daemon import run_single_daemon_iteration
from codex_supervisor.ipc import CommandInbox
from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore


def test_daemon_requeues_429_and_later_succeeds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
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


def test_daemon_creates_resume_task_from_session_log(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    fake_codex = Path(__file__).parent / "fake_codex.py"
    monkeypatch.setenv("CODEX_SUPERVISOR_CODEX_BIN", "python")
    monkeypatch.setenv("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT", str(fake_codex))

    sessions_root = tmp_path / ".codex" / "sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    session_file = sessions_root / "recover.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"resume-1","cwd":"'
                + str(tmp_path).replace("\\", "\\\\")
                + '"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"stream disconnected before completion: stream closed before response.completed","codex_error_info":"other"}}',
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(tmp_path)
    store = StateStore(config.data_dir / "supervisor.db")
    run_single_daemon_iteration(config)

    tasks = store.list_tasks(limit=10)
    assert len(tasks) == 1
    assert tasks[0].kind is TaskKind.RESUME_SESSION
    assert tasks[0].status is TaskStatus.SUCCEEDED
    log_path = config.data_dir / "logs" / f"task-{tasks[0].id}.jsonl"
    assert "resume-1" in log_path.read_text(encoding="utf-8")


def test_daemon_processes_pause_resume_and_cancel_commands(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    fake_codex = Path(__file__).parent / "fake_codex.py"
    monkeypatch.setenv("CODEX_SUPERVISOR_CODEX_BIN", "python")
    monkeypatch.setenv("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT", str(fake_codex))

    config = load_config(tmp_path)
    store = StateStore(config.data_dir / "supervisor.db")
    inbox = CommandInbox(config.data_dir / "commands")

    paused_task = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "hello"},
        priority=50,
    )
    inbox.write_command({"type": "pause", "task_id": paused_task})
    run_single_daemon_iteration(config)
    assert store.get_task(paused_task).status is TaskStatus.PAUSED

    inbox.write_command({"type": "resume", "task_id": paused_task})
    run_single_daemon_iteration(config)
    assert store.get_task(paused_task).status is TaskStatus.SUCCEEDED

    canceled_task = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "goodbye"},
        priority=50,
    )
    inbox.write_command({"type": "cancel", "task_id": canceled_task})
    run_single_daemon_iteration(config)
    assert store.get_task(canceled_task).status is TaskStatus.CANCELED


def test_daemon_marks_task_running_and_writes_launch_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    fake_codex = Path(__file__).parent / "fake_codex.py"
    monkeypatch.setenv("CODEX_SUPERVISOR_CODEX_BIN", "python")
    monkeypatch.setenv("CODEX_SUPERVISOR_FAKE_CODEX_SCRIPT", str(fake_codex))

    config = load_config(tmp_path)
    store = StateStore(config.data_dir / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "hello"},
        priority=50,
    )

    run_single_daemon_iteration(config)

    log_text = (config.data_dir / "logs" / f"task-{task_id}.jsonl").read_text(encoding="utf-8")
    assert '"source":"supervisor"' in log_text
    assert '"type":"launch"' in log_text
    assert store.get_task(task_id).status is TaskStatus.SUCCEEDED
