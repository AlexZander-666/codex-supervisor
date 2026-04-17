from dataclasses import dataclass
import json
from json import JSONDecodeError
from pathlib import Path


@dataclass(frozen=True)
class SessionFinding:
    session_id: str
    cwd: str
    reason: str
    message: str


def classify_session_file(session_path: Path) -> SessionFinding | None:
    session_id = ""
    cwd = ""
    pending_recovery: SessionFinding | None = None
    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        try:
            data = json.loads(raw_line)
        except JSONDecodeError:
            continue
        event_type = data.get("type")
        payload = data.get("payload", {})
        if event_type == "session_meta":
            session_id = payload["id"]
            cwd = payload["cwd"]
        if event_type == "event_msg" and payload.get("type") == "error":
            message = payload["message"]
            if "429 Too Many Requests" in message:
                pending_recovery = SessionFinding(
                    session_id=session_id,
                    cwd=cwd,
                    reason="http_429",
                    message=message,
                )
            elif "stream disconnected before completion" in message:
                pending_recovery = SessionFinding(
                    session_id=session_id,
                    cwd=cwd,
                    reason="stream_disconnect",
                    message=message,
                )
        if event_type == "event_msg" and payload.get("type") == "task_complete":
            pending_recovery = None
    return pending_recovery
