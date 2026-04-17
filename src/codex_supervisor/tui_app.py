from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from codex_supervisor.config import load_config
from codex_supervisor.service import (
    read_task_snapshots,
    resolve_project_root,
    write_operator_command,
)
from codex_supervisor.state import StateStore
from codex_supervisor.tui_state import TaskSnapshot
from codex_supervisor.tui_widgets import TaskDetailPane, TaskListPane, TaskOutputPane


class SupervisorTuiApp(App[None]):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("enter", "focus_task", "Focus"),
        Binding("p", "pause_task", "Pause"),
        Binding("r", "resume_task", "Resume"),
        Binding("c", "cancel_task", "Cancel"),
        Binding("l", "show_logs", "Logs"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config(resolve_project_root())
        self.store = StateStore(self.config.data_dir / "supervisor.db")
        self.snapshots: list[TaskSnapshot] = []
        self.focused_task_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield TaskListPane(id="task-list")
            with Vertical():
                yield TaskDetailPane(id="task-detail")
                yield TaskOutputPane(id="task-output")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_snapshots()
        self.set_interval(1.0, self.refresh_snapshots)

    def action_cursor_down(self) -> None:
        self._move_focus(1)

    def action_cursor_up(self) -> None:
        self._move_focus(-1)

    def action_focus_task(self) -> None:
        self._render()

    def action_pause_task(self) -> None:
        if self.focused_task_id is not None:
            write_operator_command(command_type="pause", task_id=self.focused_task_id)

    def action_resume_task(self) -> None:
        if self.focused_task_id is not None:
            write_operator_command(command_type="resume", task_id=self.focused_task_id)

    def action_cancel_task(self) -> None:
        if self.focused_task_id is not None:
            write_operator_command(command_type="cancel", task_id=self.focused_task_id)

    def action_show_logs(self) -> None:
        return

    def refresh_snapshots(self) -> None:
        self.snapshots = read_task_snapshots()
        if self.snapshots and self.focused_task_id is None:
            self.focused_task_id = self.snapshots[0].task_id
        if self.focused_task_id not in {snapshot.task_id for snapshot in self.snapshots}:
            self.focused_task_id = self.snapshots[0].task_id if self.snapshots else None
        self._render()

    def _move_focus(self, offset: int) -> None:
        if not self.snapshots:
            return
        task_ids = [snapshot.task_id for snapshot in self.snapshots]
        if self.focused_task_id not in task_ids:
            self.focused_task_id = task_ids[0]
            self._render()
            return
        index = task_ids.index(self.focused_task_id)
        index = max(0, min(len(task_ids) - 1, index + offset))
        self.focused_task_id = task_ids[index]
        self._render()

    def _render(self) -> None:
        task_list = self.query_one("#task-list", TaskListPane)
        task_detail = self.query_one("#task-detail", TaskDetailPane)
        task_output = self.query_one("#task-output", TaskOutputPane)
        focused_snapshot = next(
            (snapshot for snapshot in self.snapshots if snapshot.task_id == self.focused_task_id),
            None,
        )
        task_list.render_snapshots(
            self.snapshots,
            focused_task_id=self.focused_task_id,
        )
        task_detail.render_snapshot(focused_snapshot)
        task_output.render_snapshot(focused_snapshot)


def run_tui() -> None:
    SupervisorTuiApp().run()
