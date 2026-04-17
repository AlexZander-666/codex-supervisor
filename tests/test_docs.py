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
