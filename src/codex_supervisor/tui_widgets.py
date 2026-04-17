from textual.widgets import Static

from codex_supervisor.tui_state import TaskSnapshot


class TaskListPane(Static):
    def render_snapshots(
        self,
        snapshots: list[TaskSnapshot],
        *,
        focused_task_id: int | None,
    ) -> None:
        lines = ["Tasks"]
        for snapshot in snapshots:
            marker = ">" if snapshot.task_id == focused_task_id else " "
            lines.append(
                f"{marker} #{snapshot.task_id} [{snapshot.status}] {snapshot.stage}"
            )
        self.update("\n".join(lines))


class TaskDetailPane(Static):
    def render_snapshot(self, snapshot: TaskSnapshot | None) -> None:
        if snapshot is None:
            self.update("No supervisor tasks.")
            return
        lines = [
            f"Task #{snapshot.task_id}",
            f"Status: {snapshot.status}",
            f"Stage: {snapshot.stage}",
            f"Command: {snapshot.current_command or '-'}",
            f"Retries: {snapshot.retry_count}",
        ]
        if snapshot.error:
            lines.append(f"Error: {snapshot.error}")
        self.update("\n".join(lines))


class TaskOutputPane(Static):
    def render_snapshot(self, snapshot: TaskSnapshot | None) -> None:
        if snapshot is None:
            self.update("")
            return
        self.update(snapshot.recent_output)
