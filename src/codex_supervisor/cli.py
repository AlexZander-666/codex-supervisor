import argparse

from codex_supervisor.daemon import run_forever
from codex_supervisor.service import (
    read_task_logs,
    render_task_list,
    render_task_status,
    submit_exec_task,
    write_operator_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-supervisor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start-daemon")

    submit = subparsers.add_parser("submit")
    submit.add_argument("--cwd", required=True)
    submit.add_argument("--prompt", required=True)
    submit.add_argument("--priority", type=int, default=50)

    status = subparsers.add_parser("status")
    status.add_argument("--task-id", type=int, required=True)

    subparsers.add_parser("list")

    pause = subparsers.add_parser("pause")
    pause.add_argument("--task-id", type=int, required=True)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--task-id", type=int, required=True)

    cancel = subparsers.add_parser("cancel")
    cancel.add_argument("--task-id", type=int, required=True)

    logs = subparsers.add_parser("logs")
    logs.add_argument("--task-id", type=int, required=True)
    subparsers.add_parser("tui")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "submit":
        submit_exec_task(cwd=args.cwd, prompt=args.prompt, priority=args.priority)
        print("queued")
        return 0
    if args.command == "status":
        print(render_task_status(args.task_id))
        return 0
    if args.command == "list":
        print(render_task_list())
        return 0
    if args.command in {"pause", "resume", "cancel"}:
        write_operator_command(command_type=args.command, task_id=args.task_id)
        print(args.command)
        return 0
    if args.command == "logs":
        print(read_task_logs(args.task_id))
        return 0
    if args.command == "tui":
        from codex_supervisor.tui_app import run_tui

        run_tui()
        return 0
    if args.command == "start-daemon":
        run_forever()
        return 0
    return 0
