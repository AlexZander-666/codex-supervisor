from pathlib import Path


def test_changelog_mentions_v0_1_0_release() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "v0.1.0" in changelog
    assert "Textual" in changelog


def test_readme_mentions_release_install_and_upgrade_steps() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "## Release Install" in readme
    assert "## Upgrade" in readme
    assert "git fetch --tags" in readme


def test_readme_mentions_quick_start_flow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "## Quick Start" in readme
    assert "python -m codex_supervisor start-daemon" in readme
    assert 'codex-supervisor submit --cwd C:\\Windows\\system32 --prompt "hello"' in readme
    assert "codex-supervisor tui" in readme
