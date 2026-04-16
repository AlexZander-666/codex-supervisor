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
