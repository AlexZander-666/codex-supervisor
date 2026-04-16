import json
import sys


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:2] == ["exec", "--json"]:
        print(json.dumps({"event": "task_started", "prompt": args[-1]}))
        raise SystemExit(0)
    if args[:3] == ["exec", "resume", "--json"]:
        print(json.dumps({"event": "resumed", "session_id": args[-2]}))
        raise SystemExit(0)
    raise SystemExit(1)
