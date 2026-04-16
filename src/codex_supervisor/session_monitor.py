from pathlib import Path

from codex_supervisor.log_parser import SessionFinding, classify_session_file


class SessionMonitor:
    def __init__(self, sessions_root: Path) -> None:
        self.sessions_root = sessions_root
        self.seen_keys: set[tuple[str, str]] = set()

    def scan(self) -> list[SessionFinding]:
        findings: list[SessionFinding] = []
        for session_file in self.sessions_root.rglob("*.jsonl"):
            finding = classify_session_file(session_file)
            if finding is None:
                continue
            dedupe_key = (finding.session_id, finding.reason)
            if dedupe_key in self.seen_keys:
                continue
            self.seen_keys.add(dedupe_key)
            findings.append(finding)
        return findings
