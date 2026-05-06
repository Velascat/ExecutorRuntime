# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import UTC, datetime

from executor_runtime.contracts.result import RuntimeResult


def test_result_defaults_artifacts_to_empty_list() -> None:
    now = datetime.now(UTC).isoformat()
    result = RuntimeResult(
        invocation_id="inv-1",
        runtime_name="local",
        runtime_kind="subprocess",
        status="succeeded",
        exit_code=0,
        started_at=now,
        finished_at=now,
        stdout_path=None,
        stderr_path=None,
    )
    assert result.artifacts == []
