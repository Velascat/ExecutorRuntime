from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeInvocation:
    invocation_id: str
    runtime_name: str
    working_directory: str
    command: list[str]
    environment: dict[str, str]
    timeout_seconds: int | None
    input_payload_path: str | None
    output_result_path: str | None
    artifact_directory: str | None

    def __post_init__(self) -> None:
        if not self.invocation_id.strip():
            msg = "invocation_id must be non-empty"
            raise ValueError(msg)
        if not self.runtime_name.strip():
            msg = "runtime_name must be non-empty"
            raise ValueError(msg)
        if not self.working_directory.strip():
            msg = "working_directory must be non-empty"
            raise ValueError(msg)
        if not self.command:
            msg = "command must be non-empty"
            raise ValueError(msg)
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            msg = "timeout_seconds must be greater than zero when provided"
            raise ValueError(msg)
