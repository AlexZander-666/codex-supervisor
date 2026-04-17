# Changelog

All notable changes to this project will be documented in this file.

## v0.1.0 - 2026-04-17

Initial public release.

- Add the Windows-first supervisor CLI with `submit`, `status`, `list`, `pause`, `resume`, `cancel`, `logs`, and `start-daemon`.
- Detect `429 Too Many Requests` and `stream disconnected before completion`, then re-enqueue recovery with `codex exec resume`.
- Add a Textual terminal TUI for structured live monitoring, recent output tails, retry/error display, and operator controls.
