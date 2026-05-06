from datetime import UTC, datetime

from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.contracts.status import RuntimeStatus


def test_result_defaults_artifacts_to_empty_list() -> None:
    now = datetime.now(UTC).isoformat()
    result = RuntimeResult(
        invocation_id="inv-1",
        runtime_name="local",
        status=RuntimeStatus.SUCCEEDED,
        exit_code=0,
        started_at=now,
        finished_at=now,
        stdout_path=None,
        stderr_path=None,
    )
    assert result.artifacts == []
