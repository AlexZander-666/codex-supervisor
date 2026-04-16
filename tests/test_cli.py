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
