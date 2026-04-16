from pathlib import Path

from codex_supervisor.config import SupervisorConfig


def commands_dir(config: SupervisorConfig) -> Path:
    return config.data_dir / "commands"


def logs_dir(config: SupervisorConfig) -> Path:
    return config.data_dir / "logs"


def state_db_path(config: SupervisorConfig) -> Path:
    return config.data_dir / "supervisor.db"
