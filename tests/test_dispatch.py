# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for dispatch-by-runtime_kind in ExecutorRuntime."""
from datetime import UTC, datetime

import pytest

from executor_runtime import ExecutorRuntime
from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.runners.manual_runner import ManualRunner


def _invocation(*, runtime_kind: str = "subprocess") -> RuntimeInvocation:
    return RuntimeInvocation(
        invocation_id="inv-1",
        runtime_name="example",
        runtime_kind=runtime_kind,
        working_directory="/tmp",
        command=["echo", "hi"],
        environment={},
        timeout_seconds=5,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )


def _result_for(invocation: RuntimeInvocation) -> RuntimeResult:
    now = datetime.now(UTC).isoformat()
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="succeeded",
        exit_code=0,
        started_at=now,
        finished_at=now,
        stdout_path=None,
        stderr_path=None,
    )


def test_default_constructor_handles_subprocess_kind() -> None:
    """No-arg constructor still serves subprocess invocations."""
    runtime = ExecutorRuntime()
    # We don't actually run a real subprocess here — just confirm the
    # subprocess runner is the default for runtime_kind="subprocess".
    runner = runtime._runners["subprocess"]
    assert runner is not None


def test_unregistered_runtime_kind_returns_rejected() -> None:
    runtime = ExecutorRuntime()
    inv = _invocation(runtime_kind="manual")
    result = runtime.run(inv)
    assert result.status == "rejected"
    assert "no runner registered" in (result.error_summary or "")
    assert "manual" in (result.error_summary or "")


def test_register_then_dispatch_routes_by_kind() -> None:
    received: list[RuntimeInvocation] = []

    def dispatcher(invocation: RuntimeInvocation) -> RuntimeResult:
        received.append(invocation)
        return _result_for(invocation)

    runtime = ExecutorRuntime()
    runtime.register("manual", ManualRunner(dispatcher))

    inv = _invocation(runtime_kind="manual")
    result = runtime.run(inv)

    assert received == [inv]
    assert result.status == "succeeded"


def test_runners_kwarg_constructor_supports_multiple_kinds() -> None:
    sub_called: list[RuntimeInvocation] = []
    man_called: list[RuntimeInvocation] = []

    def sub(invocation):
        sub_called.append(invocation)
        return _result_for(invocation)

    def man(invocation):
        man_called.append(invocation)
        return _result_for(invocation)

    runtime = ExecutorRuntime(
        runners={
            "subprocess": ManualRunner(sub),  # use ManualRunner-as-fake for this test
            "manual": ManualRunner(man),
        },
    )

    runtime.run(_invocation(runtime_kind="subprocess"))
    runtime.run(_invocation(runtime_kind="manual"))

    assert len(sub_called) == 1
    assert len(man_called) == 1


def test_legacy_runner_kwarg_still_works() -> None:
    """Pre-dispatch ExecutorRuntime(runner=...) constructor."""
    received: list[RuntimeInvocation] = []

    def fake_subprocess(invocation):
        received.append(invocation)
        return _result_for(invocation)

    runtime = ExecutorRuntime(runner=ManualRunner(fake_subprocess))
    inv = _invocation(runtime_kind="subprocess")
    result = runtime.run(inv)

    assert result.status == "succeeded"
    assert len(received) == 1


@pytest.mark.parametrize("kind", ["http", "container", "unknown"])
def test_known_rxp_kinds_with_no_registered_runner_get_rejected(kind: str) -> None:
    runtime = ExecutorRuntime()
    inv = _invocation(runtime_kind=kind)
    result = runtime.run(inv)
    assert result.status == "rejected"
