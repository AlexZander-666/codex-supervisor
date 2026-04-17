from codex_supervisor.cli import build_parser
from codex_supervisor.tui_app import SupervisorTuiApp


def test_cli_has_tui_command() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "tui" in choices


def test_tui_app_exposes_expected_keybindings() -> None:
    app = SupervisorTuiApp()
    bindings = {binding.key for binding in app.BINDINGS}
    assert {"q", "j", "k", "enter", "p", "r", "c", "l"} <= bindings
