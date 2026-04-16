from pathlib import Path

from codex_supervisor.cli import main
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
    from codex_supervisor.models import TaskKind
    from codex_supervisor.state import StateStore

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
    from codex_supervisor.models import TaskKind
    from codex_supervisor.state import StateStore

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


def test_pause_and_resume_write_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    from codex_supervisor.models import TaskKind
    from codex_supervisor.state import StateStore

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
