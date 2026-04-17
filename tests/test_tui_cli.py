import json
from pathlib import Path

from codex_supervisor.cli import build_parser
from codex_supervisor.models import TaskKind
from codex_supervisor.state import StateStore
from codex_supervisor.tui_app import SupervisorTuiApp


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
