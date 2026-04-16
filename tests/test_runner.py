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
