# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Velascat
import sys
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.runners.subprocess_runner import SubprocessRunner
from executor_runtime.runtime import ExecutorRuntime


def test_default_facade_uses_subprocess_runner() -> None:
    runtime = ExecutorRuntime()
    assert isinstance(runtime.runner, SubprocessRunner)


def test_facade_returns_runtime_result(tmp_path: Path) -> None:
    runtime = ExecutorRuntime()
    invocation = RuntimeInvocation(
        invocation_id="inv-facade",
        runtime_name="local",
        runtime_kind="subprocess",
        working_directory=str(tmp_path),
        command=[sys.executable, "-c", "print('facade')"],
        environment={},
        timeout_seconds=5,
        input_payload_path=None,
        output_result_path=str(tmp_path / "result.json"),
        artifact_directory=None,
    )

    result = runtime.run(invocation)
    assert isinstance(result, RuntimeResult)
    assert (tmp_path / "result.json").exists()
