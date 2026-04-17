from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static


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

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Static(id="task-list")
            with Vertical():
                yield Static(id="task-detail")
                yield Static(id="task-output")
        yield Footer()


def run_tui() -> None:
    SupervisorTuiApp().run()
