from dataclasses import dataclass
import json
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
    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        data = json.loads(raw_line)
        if data["type"] == "session_meta":
            session_id = data["payload"]["id"]
            cwd = data["payload"]["cwd"]
        if data["type"] == "event_msg" and data["payload"]["type"] == "error":
            message = data["payload"]["message"]
            if "429 Too Many Requests" in message:
                return SessionFinding(
                    session_id=session_id,
                    cwd=cwd,
                    reason="http_429",
                    message=message,
                )
            if "stream disconnected before completion" in message:
                return SessionFinding(
                    session_id=session_id,
                    cwd=cwd,
                    reason="stream_disconnect",
                    message=message,
                )
    return None
