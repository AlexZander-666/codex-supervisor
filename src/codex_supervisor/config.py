from dataclasses import dataclass
import os
from pathlib import Path
import shutil


@dataclass(frozen=True)
class SupervisorConfig:
    project_root: Path
    data_dir: Path
    codex_home: Path
    max_concurrency: int = 2
    monitor_interval_seconds: int = 15
    scheduler_interval_seconds: int = 2
    retry_base_seconds: int = 30
    retry_cap_seconds: int = 600
    codex_bin: str = "codex"


def load_config(project_root: Path) -> SupervisorConfig:
    data_dir = project_root / "data"
    codex_home = Path(os.environ.get("CODEX_HOME", r"C:\Users\black\.codex"))
    codex_bin = os.environ.get("CODEX_SUPERVISOR_CODEX_BIN")
    if codex_bin is None:
        codex_bin = shutil.which("codex") or shutil.which("codex.cmd") or "codex"
        if codex_bin == "codex":
            appdata = os.environ.get("APPDATA")
            if appdata:
                codex_cmd = Path(appdata) / "npm" / "codex.cmd"
                if codex_cmd.exists():
                    codex_bin = str(codex_cmd)
    return SupervisorConfig(
        project_root=project_root,
        data_dir=data_dir,
        codex_home=codex_home,
        codex_bin=codex_bin,
    )
