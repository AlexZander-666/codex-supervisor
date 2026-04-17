from pathlib import Path

from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore
from codex_supervisor.tui_state import build_task_snapshot, load_task_snapshots


def test_build_task_snapshot_extracts_structured_runtime_fields(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.RESUME_SESSION,
        cwd=r"C:\work\repo",
        payload={"session_id": "session-1", "prompt": "continue"},
        priority=100,
        session_id="session-1",
    )
    store.transition_task(task_id, TaskStatus.RUNNING, lease_owner="daemon-main")
    log_path = tmp_path / "task-1.jsonl"
    log_path.write_text(
        "\n".join(
            [
                '{"source":"supervisor","type":"launch","command":["codex","exec","resume","--json","session-1","continue"],"cwd":"C:\\\\work\\\\repo"}',
                '{"type":"thread.started","thread_id":"session-1"}',
                '{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"powershell -Command pnpm type-check","status":"in_progress"}}',
                '{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"继续排查登录分支同步问题。"}}',
            ]
        ),
        encoding="utf-8",
    )

    snapshot = build_task_snapshot(store.get_task(task_id), log_path)

    assert snapshot.task_id == task_id
    assert snapshot.status == "running"
    assert snapshot.current_command == "powershell -Command pnpm type-check"
    assert snapshot.stage == "command_execution"
    assert snapshot.retry_count == 0
    assert "继续排查登录分支同步问题" in snapshot.recent_output


def test_load_task_snapshots_orders_active_tasks_first(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "supervisor.db")
    first = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "one"},
        priority=50,
    )
    second = store.create_task(
        kind=TaskKind.RESUME_SESSION,
        cwd=str(tmp_path),
        payload={"session_id": "session-2", "prompt": "continue"},
        priority=100,
        session_id="session-2",
    )
    store.transition_task(first, TaskStatus.SUCCEEDED, lease_owner=None)
    store.transition_task(second, TaskStatus.RUNNING, lease_owner="daemon-main")

    snapshots = load_task_snapshots(store, tmp_path)

    assert [snapshot.task_id for snapshot in snapshots][:2] == [second, first]


def test_build_task_snapshot_truncates_recent_output_to_last_lines(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "tail"},
        priority=50,
    )
    log_path = tmp_path / "task.jsonl"
    log_path.write_text(
        "\n".join(
            f'{{"type":"item.completed","item":{{"type":"agent_message","text":"line-{index}"}}}}'
            for index in range(20)
        ),
        encoding="utf-8",
    )

    snapshot = build_task_snapshot(store.get_task(task_id), log_path)

    assert "line-12" in snapshot.recent_output
    assert "line-19" in snapshot.recent_output
    assert "line-11" not in snapshot.recent_output
    assert "line-0" not in snapshot.recent_output
