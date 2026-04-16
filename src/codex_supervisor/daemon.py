import os
from pathlib import Path
import time


def acquire_daemon_lock(lock_path: Path) -> Path | None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))

    return lock_path


def run_forever() -> None:
    while True:
        time.sleep(60)
