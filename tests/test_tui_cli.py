from codex_supervisor.cli import build_parser


def test_cli_has_tui_command() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "tui" in choices
