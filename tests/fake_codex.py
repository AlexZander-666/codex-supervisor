import json
from pathlib import Path
import sys


if __name__ == "__main__":
    args = sys.argv[1:]
    session_file = Path(".fake_codex_429_once")
    if args[:1] == ["exec"]:
        prompt = args[-1]
        print(
            json.dumps(
                {
                    "timestamp": "2026-04-16T15:28:09Z",
                    "type": "session_meta",
                    "payload": {"id": "fake-session", "cwd": str(Path.cwd())},
                }
            )
        )
        if prompt == "trigger 429 once" and not session_file.exists():
            session_file.write_text("seen", encoding="utf-8")
            print(
                json.dumps(
                    {
                        "timestamp": "2026-04-16T15:28:10Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "error",
                            "message": "exceeded retry limit, last status: 429 Too Many Requests",
                            "codex_error_info": {
                                "response_too_many_failed_attempts": {
                                    "http_status_code": 429
                                }
                            },
                        },
                    }
                )
            )
            raise SystemExit(1)
        print(json.dumps({"event": "task_started", "prompt": prompt}))
        raise SystemExit(0)
    if args[:1] == ["resume"]:
        print(
            json.dumps(
                {
                    "timestamp": "2026-04-16T15:28:09Z",
                    "type": "session_meta",
                    "payload": {"id": args[-2], "cwd": str(Path.cwd())},
                }
            )
        )
        print(json.dumps({"event": "resumed", "session_id": args[-2]}))
        raise SystemExit(0)
    raise SystemExit(1)
