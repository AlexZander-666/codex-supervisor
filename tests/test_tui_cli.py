import asyncio
import json
from pathlib import Path
import sqlite3

from codex_supervisor.cli import build_parser
from codex_supervisor.models import TaskKind, TaskStatus
from codex_supervisor.state import StateStore
from codex_supervisor.tui_app import SupervisorTuiApp


def _write_task_log(log_path: Path, *lines: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines), encoding="utf-8")


def _create_tui_task(
    store: StateStore,
    data_dir: Path,
    *,
    prompt: str,
    status: TaskStatus,
    recent_output: str,
) -> int:
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(data_dir),
        payload={"prompt": prompt},
        priority=50,
    )
    store.transition_task(task_id, status, lease_owner="daemon-main" if status is TaskStatus.RUNNING else None)
    _write_task_log(
        data_dir / "logs" / f"task-{task_id}.jsonl",
        '{"type":"item.started","item":{"type":"command_execution","command":"powershell -Command echo hello"}}',
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": recent_output},
            },
            ensure_ascii=False,
        ),
    )
    return task_id


def _delete_task(db_path: Path, task_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def test_cli_has_tui_command() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "tui" in choices


def test_tui_app_exposes_expected_keybindings() -> None:
    app = SupervisorTuiApp()
    bindings = {binding.key for binding in app.BINDINGS}
    assert {"q", "j", "k", "enter", "p", "r", "c", "l"} <= bindings


def test_pause_resume_cancel_write_commands_for_tui(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    store = StateStore(tmp_path / "data" / "supervisor.db")
    task_id = store.create_task(
        kind=TaskKind.EXEC_PROMPT,
        cwd=str(tmp_path),
        payload={"prompt": "hello"},
        priority=50,
    )

    app = SupervisorTuiApp()
    app.focused_task_id = task_id
    app.action_pause_task()
    app.action_resume_task()
    app.action_cancel_task()

    files = sorted((tmp_path / "data" / "commands").glob("*.json"))
    assert len(files) == 3
    assert sorted(json.loads(path.read_text(encoding="utf-8"))["type"] for path in files) == [
        "cancel",
        "pause",
        "resume",
    ]


def test_readme_mentions_tui_command() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "codex-supervisor tui" in readme


def test_tui_navigation_updates_detail_and_output_panes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    store = StateStore(data_dir / "supervisor.db")
    first_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="first",
        status=TaskStatus.SUCCEEDED,
        recent_output="first-output",
    )
    second_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="second",
        status=TaskStatus.RUNNING,
        recent_output="second-output",
    )

    async def run_scenario() -> None:
        app = SupervisorTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert f"Task #{second_task_id}" in str(app.query_one("#task-detail").renderable)
            assert "second-output" in str(app.query_one("#task-output").renderable)

            await pilot.press("j")
            await pilot.pause()
            assert f"Task #{first_task_id}" in str(app.query_one("#task-detail").renderable)
            assert "first-output" in str(app.query_one("#task-output").renderable)

            await pilot.press("k")
            await pilot.pause()
            assert f"Task #{second_task_id}" in str(app.query_one("#task-detail").renderable)
            assert "second-output" in str(app.query_one("#task-output").renderable)

    asyncio.run(run_scenario())


def test_tui_keybindings_enqueue_operator_commands_for_focused_task(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    store = StateStore(data_dir / "supervisor.db")
    task_id = _create_tui_task(
        store,
        data_dir,
        prompt="interactive",
        status=TaskStatus.RUNNING,
        recent_output="operator-output",
    )

    async def run_scenario() -> None:
        app = SupervisorTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert f"Task #{task_id}" in str(app.query_one("#task-detail").renderable)

            await pilot.press("p", "r", "c")
            await pilot.pause()

        files = sorted((data_dir / "commands").glob("*.json"))
        assert len(files) == 3
        assert sorted(
            json.loads(path.read_text(encoding="utf-8"))["type"] for path in files
        ) == ["cancel", "pause", "resume"]
        assert {
            json.loads(path.read_text(encoding="utf-8"))["task_id"] for path in files
        } == {task_id}

    asyncio.run(run_scenario())


def test_tui_polling_refreshes_status_error_and_recent_output(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    store = StateStore(data_dir / "supervisor.db")
    task_id = _create_tui_task(
        store,
        data_dir,
        prompt="refresh",
        status=TaskStatus.RUNNING,
        recent_output="before-refresh",
    )
    log_path = data_dir / "logs" / f"task-{task_id}.jsonl"

    async def run_scenario() -> None:
        app = SupervisorTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "Status: running" in str(app.query_one("#task-detail").renderable)
            assert "before-refresh" in str(app.query_one("#task-output").renderable)

            store.increment_attempt_count(task_id)
            store.transition_task(task_id, TaskStatus.BACKING_OFF, lease_owner=None)
            log_path.write_text(
                "\n".join(
                    [
                        '{"type":"item.started","item":{"type":"command_execution","command":"powershell -Command echo hello"}}',
                        '{"type":"event_msg","payload":{"type":"error","message":"stream disconnected before completion"}}',
                        '{"type":"item.completed","item":{"type":"agent_message","text":"after-refresh"}}',
                    ]
                ),
                encoding="utf-8",
            )

            await asyncio.sleep(1.2)
            await pilot.pause()

            detail = str(app.query_one("#task-detail").renderable)
            output = str(app.query_one("#task-output").renderable)
            assert "Status: backing_off" in detail
            assert "Retries: 1" in detail
            assert "Error: stream disconnected before completion" in detail
            assert "after-refresh" in output

    asyncio.run(run_scenario())


def test_tui_refresh_falls_back_when_focused_task_disappears_and_queue_empties(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    db_path = data_dir / "supervisor.db"
    store = StateStore(db_path)
    fallback_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="fallback",
        status=TaskStatus.SUCCEEDED,
        recent_output="fallback-output",
    )
    focused_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="focused",
        status=TaskStatus.RUNNING,
        recent_output="focused-output",
    )

    async def run_scenario() -> None:
        app = SupervisorTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert f"Task #{focused_task_id}" in str(app.query_one("#task-detail").renderable)

            _delete_task(db_path, focused_task_id)
            await asyncio.sleep(1.2)
            await pilot.pause()

            assert app.focused_task_id == fallback_task_id
            assert f"Task #{fallback_task_id}" in str(app.query_one("#task-detail").renderable)
            assert "fallback-output" in str(app.query_one("#task-output").renderable)

            _delete_task(db_path, fallback_task_id)
            await asyncio.sleep(1.2)
            await pilot.pause()

            assert app.focused_task_id is None
            assert str(app.query_one("#task-list").renderable) == "Tasks"
            assert str(app.query_one("#task-detail").renderable) == "No supervisor tasks."
            assert str(app.query_one("#task-output").renderable) == ""

    asyncio.run(run_scenario())


def test_tui_refresh_reorders_tasks_without_stealing_focus_from_existing_task(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    store = StateStore(data_dir / "supervisor.db")
    oldest_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="oldest",
        status=TaskStatus.SUCCEEDED,
        recent_output="oldest-output",
    )
    initially_focused_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="focused",
        status=TaskStatus.RUNNING,
        recent_output="focused-output",
    )
    stable_task_id = _create_tui_task(
        store,
        data_dir,
        prompt="stable",
        status=TaskStatus.SUCCEEDED,
        recent_output="stable-output",
    )

    async def run_scenario() -> None:
        app = SupervisorTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("j")
            await pilot.pause()

            assert app.focused_task_id == stable_task_id
            assert f"Task #{stable_task_id}" in str(app.query_one("#task-detail").renderable)

            store.transition_task(oldest_task_id, TaskStatus.RUNNING, lease_owner="daemon-main")
            store.transition_task(
                initially_focused_task_id,
                TaskStatus.SUCCEEDED,
                lease_owner=None,
            )
            await asyncio.sleep(1.2)
            await pilot.pause()

            assert app.focused_task_id == stable_task_id
            assert f"Task #{stable_task_id}" in str(app.query_one("#task-detail").renderable)

            task_list = str(app.query_one("#task-list").renderable)
            assert task_list.index(f"#%s [running]" % oldest_task_id) < task_list.index(
                f"#%s [succeeded]" % stable_task_id
            )
            assert task_list.index(f"#%s [succeeded]" % stable_task_id) < task_list.index(
                f"#%s [succeeded]" % initially_focused_task_id
            )

    asyncio.run(run_scenario())
