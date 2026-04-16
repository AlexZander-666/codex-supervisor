import json
from pathlib import Path
import uuid


class CommandInbox:
    def __init__(self, inbox_dir: Path) -> None:
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def write_command(self, command: dict) -> Path:
        temp_path = self.inbox_dir / f".{uuid.uuid4().hex}.tmp"
        final_path = self.inbox_dir / f"{uuid.uuid4().hex}.json"
        temp_path.write_text(json.dumps(command), encoding="utf-8")
        temp_path.replace(final_path)
        return final_path

    def read_next_command(self) -> dict | None:
        files = sorted(self.inbox_dir.glob("*.json"))
        if not files:
            return None
        path = files[0]
        data = json.loads(path.read_text(encoding="utf-8"))
        path.unlink()
        return data
