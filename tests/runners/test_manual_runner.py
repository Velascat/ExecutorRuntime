# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import UTC, datetime

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.runners.manual_runner import ManualRunner


def _invocation(**overrides) -> RuntimeInvocation:
    defaults = dict(
        invocation_id="inv-1",
        runtime_name="archon",
        runtime_kind="manual",
        working_directory="/tmp",
        command=["archon-workflow", "--run-id", "inv-1"],
        environment={},
        timeout_seconds=300,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )
    defaults.update(overrides)
    return RuntimeInvocation(**defaults)


def _result_for(invocation: RuntimeInvocation, *, status: str = "succeeded") -> RuntimeResult:
    now = datetime.now(UTC).isoformat()
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status=status,
        exit_code=0 if status == "succeeded" else 1,
        started_at=now,
        finished_at=now,
        stdout_path=None,
        stderr_path=None,
    )


def test_dispatcher_receives_invocation_and_returns_result() -> None:
    received: list[RuntimeInvocation] = []

    def dispatcher(invocation: RuntimeInvocation) -> RuntimeResult:
        received.append(invocation)
        return _result_for(invocation, status="succeeded")

    runner = ManualRunner(dispatcher)
    inv = _invocation()
    result = runner.run(inv)

    assert received == [inv]
    assert result.status == "succeeded"
    assert result.invocation_id == "inv-1"


def test_dispatcher_can_synthesize_failure() -> None:
    def dispatcher(invocation: RuntimeInvocation) -> RuntimeResult:
        return _result_for(invocation, status="failed")

    result = ManualRunner(dispatcher).run(_invocation())
    assert result.status == "failed"
    assert result.exit_code == 1
