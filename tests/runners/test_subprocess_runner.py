# SPDX-License-Identifier: AGPL-3.0-or-later
import sys
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.runners.subprocess_runner import SubprocessRunner


def _invocation(tmp_path: Path, command: list[str], **overrides) -> RuntimeInvocation:
    defaults = dict(
        invocation_id="inv-1",
        runtime_name="subprocess",
        runtime_kind="subprocess",
        working_directory=str(tmp_path),
        command=command,
        environment={},
        timeout_seconds=1,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )
    defaults.update(overrides)
    return RuntimeInvocation(**defaults)


def test_successful_command_returns_succeeded(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "print('ok')"])
    result = SubprocessRunner().run(inv)
    assert result.status == "succeeded"
    assert result.exit_code == 0
    assert result.runtime_kind == "subprocess"


def test_failing_command_returns_failed(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "import sys; sys.exit(7)"])
    result = SubprocessRunner().run(inv)
    assert result.status == "failed"
    assert result.exit_code == 7


def test_timeout_command_returns_timed_out(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "import time; time.sleep(2)"])
    result = SubprocessRunner().run(inv)
    assert result.status == "timed_out"


def test_missing_working_directory_returns_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    inv = _invocation(
        tmp_path, [sys.executable, "-c", "print('x')"],
        invocation_id="inv-missing",
        working_directory=str(missing),
        timeout_seconds=5,
    )
    result = SubprocessRunner().run(inv)
    assert result.status == "rejected"
    assert result.stdout_path is None
    assert result.stderr_path is None


def test_stdout_and_stderr_written(tmp_path: Path) -> None:
    inv = _invocation(
        tmp_path,
        [
            sys.executable,
            "-c",
            "import sys; print('hello-out'); print('hello-err', file=sys.stderr)",
        ],
        timeout_seconds=5,
    )
    result = SubprocessRunner().run(inv)

    assert "hello-out" in Path(result.stdout_path or "").read_text(encoding="utf-8")
    assert "hello-err" in Path(result.stderr_path or "").read_text(encoding="utf-8")


def test_environment_overlay_visible_to_child_process(tmp_path: Path) -> None:
    inv = _invocation(
        tmp_path,
        [sys.executable, "-c", "import os; print(os.environ['EXAMPLE_VAR'])"],
        invocation_id="inv-env",
        environment={"EXAMPLE_VAR": "visible"},
        timeout_seconds=5,
    )
    result = SubprocessRunner().run(inv)
    stdout = Path(result.stdout_path or "").read_text(encoding="utf-8")

    assert result.status == "succeeded"
    assert "visible" in stdout


def test_artifacts_returned_as_artifact_descriptors(tmp_path: Path) -> None:
    inv = _invocation(
        tmp_path, [sys.executable, "-c", "print('hi')"], timeout_seconds=5,
    )
    result = SubprocessRunner().run(inv)
    assert len(result.artifacts) == 2
    ids = {a.artifact_id for a in result.artifacts}
    assert ids == {"stdout", "stderr"}
    for art in result.artifacts:
        assert art.path
        assert art.kind == "log_excerpt"
