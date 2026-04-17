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


def test_classify_session_ignores_truncated_json_line(tmp_path: Path) -> None:
    session_file = tmp_path / "truncated.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-3","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"exec_output","message":"unterminated"',
                '{"timestamp":"2026-04-16T15:28:11Z","type":"event_msg","payload":{"type":"error","message":"stream disconnected before completion: stream closed before response.completed","codex_error_info":"other"}}',
            ]
        ),
        encoding="utf-8",
    )
    finding = classify_session_file(session_file)
    assert finding is not None
    assert finding.reason == "stream_disconnect"


def test_classify_session_ignores_recoverable_error_after_later_completion(
    tmp_path: Path,
) -> None:
    session_file = tmp_path / "completed-after-error.jsonl"
    session_file.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-16T15:28:09Z","type":"session_meta","payload":{"id":"s-4","cwd":"C:\\\\Windows\\\\system32"}}',
                '{"timestamp":"2026-04-16T15:28:10Z","type":"event_msg","payload":{"type":"error","message":"exceeded retry limit, last status: 429 Too Many Requests","codex_error_info":{"response_too_many_failed_attempts":{"http_status_code":429}}}}',
                '{"timestamp":"2026-04-16T15:28:11Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":10,"cached_input_tokens":0,"output_tokens":2,"reasoning_output_tokens":0,"total_tokens":12},"last_token_usage":{"input_tokens":10,"cached_input_tokens":0,"output_tokens":2,"reasoning_output_tokens":0,"total_tokens":12},"model_context_window":258400},"rate_limits":{"limit_id":"codex"}}}',
                '{"timestamp":"2026-04-16T15:28:12Z","type":"event_msg","payload":{"type":"task_complete","turn_id":"turn-1","completed_at":1776353292,"duration_ms":4000}}',
            ]
        ),
        encoding="utf-8",
    )

    finding = classify_session_file(session_file)
    assert finding is None
