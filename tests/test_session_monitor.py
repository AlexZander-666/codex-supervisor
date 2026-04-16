from pathlib import Path

from codex_supervisor.log_parser import classify_session_file


def test_classify_429_session(tmp_path: Path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-1","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"exceeded retry limit, last status: 429 Too Many Requests","codex_error_info":{"response_too_many_failed_attempts":{"http_status_code":429}}}}',
            ]
        ),
        encoding="utf-8",
    )
    finding = classify_session_file(session_file)
    assert finding.session_id == "s-1"
    assert finding.reason == "http_429"


def test_classify_disconnect_session(tmp_path: Path) -> None:
    session_file = tmp_path / "disconnect.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-2","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"stream disconnected before completion: stream closed before response.completed","codex_error_info":"other"}}',
            ]
        ),
        encoding="utf-8",
    )
    finding = classify_session_file(session_file)
    assert finding.session_id == "s-2"
    assert finding.reason == "stream_disconnect"
