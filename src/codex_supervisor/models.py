from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskKind(str, Enum):
    EXEC_PROMPT = "exec_prompt"
    RESUME_SESSION = "resume_session"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    LAUNCHING = "launching"
    RUNNING = "running"
    BACKING_OFF = "backing_off"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class TaskRecord:
    id: int
    kind: TaskKind
    status: TaskStatus
    cwd: str
    payload: dict[str, Any]
    priority: int
    lease_owner: str | None
    attempt_count: int
