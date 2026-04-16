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
