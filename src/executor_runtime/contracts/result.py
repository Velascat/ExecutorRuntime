from dataclasses import dataclass, field
from datetime import datetime

from executor_runtime.contracts.status import RuntimeStatus


@dataclass(slots=True)
class RuntimeResult:
    invocation_id: str
    runtime_name: str
    status: RuntimeStatus
    exit_code: int | None
    started_at: str
    finished_at: str
    stdout_path: str | None
    stderr_path: str | None
    artifacts: list[str] = field(default_factory=list)
    error_summary: str | None = None

    def __post_init__(self) -> None:
        if not self.invocation_id.strip():
            msg = "invocation_id must be non-empty"
            raise ValueError(msg)
        if not self.runtime_name.strip():
            msg = "runtime_name must be non-empty"
            raise ValueError(msg)

        self._parse_iso(self.started_at, field_name="started_at")
        self._parse_iso(self.finished_at, field_name="finished_at")

    @staticmethod
    def _parse_iso(value: str, *, field_name: str) -> None:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            msg = f"{field_name} must be ISO-compatible"
            raise ValueError(msg) from exc
