import sys
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.status import RuntimeStatus
from executor_runtime.runners.subprocess_runner import SubprocessRunner


def _invocation(tmp_path: Path, command: list[str]) -> RuntimeInvocation:
    return RuntimeInvocation(
        invocation_id="inv-1",
        runtime_name="subprocess",
        working_directory=str(tmp_path),
        command=command,
        environment={},
        timeout_seconds=1,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )


def test_successful_command_returns_succeeded(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "print('ok')"])
    result = SubprocessRunner().run(inv)
    assert result.status == RuntimeStatus.SUCCEEDED
    assert result.exit_code == 0


def test_failing_command_returns_failed(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "import sys; sys.exit(7)"])
    result = SubprocessRunner().run(inv)
    assert result.status == RuntimeStatus.FAILED
    assert result.exit_code == 7


def test_timeout_command_returns_timed_out(tmp_path: Path) -> None:
    inv = _invocation(tmp_path, [sys.executable, "-c", "import time; time.sleep(2)"])
    result = SubprocessRunner().run(inv)
    assert result.status == RuntimeStatus.TIMED_OUT


def test_missing_working_directory_returns_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    inv = RuntimeInvocation(
        invocation_id="inv-missing",
        runtime_name="subprocess",
        working_directory=str(missing),
        command=[sys.executable, "-c", "print('x')"],
        environment={},
        timeout_seconds=5,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )
    result = SubprocessRunner().run(inv)
    assert result.status == RuntimeStatus.REJECTED
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
    )
    result = SubprocessRunner().run(inv)

    assert "hello-out" in Path(result.stdout_path or "").read_text(encoding="utf-8")
    assert "hello-err" in Path(result.stderr_path or "").read_text(encoding="utf-8")


def test_environment_overlay_visible_to_child_process(tmp_path: Path) -> None:
    inv = RuntimeInvocation(
        invocation_id="inv-env",
        runtime_name="subprocess",
        working_directory=str(tmp_path),
        command=[sys.executable, "-c", "import os; print(os.environ['EXAMPLE_VAR'])"],
        environment={"EXAMPLE_VAR": "visible"},
        timeout_seconds=5,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )
    result = SubprocessRunner().run(inv)
    stdout = Path(result.stdout_path or "").read_text(encoding="utf-8")

    assert result.status == RuntimeStatus.SUCCEEDED
    assert "visible" in stdout
