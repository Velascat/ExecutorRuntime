from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.contracts.status import RuntimeStatus
from executor_runtime.io.paths import capture_directory


class SubprocessRunner:
    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        started_at = _utc_now_iso()
        working_dir = Path(invocation.working_directory)
        if not working_dir.exists() or not working_dir.is_dir():
            finished_at = _utc_now_iso()
            return RuntimeResult(
                invocation_id=invocation.invocation_id,
                runtime_name=invocation.runtime_name,
                status=RuntimeStatus.REJECTED,
                exit_code=None,
                started_at=started_at,
                finished_at=finished_at,
                stdout_path=None,
                stderr_path=None,
                artifacts=[],
                error_summary=f"working directory does not exist: {working_dir}",
            )

        out_dir = capture_directory(invocation)
        out_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = out_dir / "stdout.txt"
        stderr_path = out_dir / "stderr.txt"

        env = os.environ.copy()
        env.update(invocation.environment)

        try:
            with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
                completed = subprocess.run(
                    invocation.command,
                    cwd=working_dir,
                    env=env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    check=False,
                    timeout=invocation.timeout_seconds,
                    shell=False,
                )
            status = RuntimeStatus.SUCCEEDED if completed.returncode == 0 else RuntimeStatus.FAILED
            exit_code = completed.returncode
            error_summary = None
        except subprocess.TimeoutExpired as exc:
            status = RuntimeStatus.TIMED_OUT
            exit_code = None
            error_summary = (
                f"process exceeded timeout of {invocation.timeout_seconds} seconds"
                if invocation.timeout_seconds
                else "process timed out"
            )
            _append_timeout_output(stdout_path, exc.stdout)
            _append_timeout_output(stderr_path, exc.stderr)

        finished_at = _utc_now_iso()
        artifacts = [str(stdout_path), str(stderr_path)]

        return RuntimeResult(
            invocation_id=invocation.invocation_id,
            runtime_name=invocation.runtime_name,
            status=status,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            artifacts=artifacts,
            error_summary=error_summary,
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _append_timeout_output(path: Path, data: bytes | str | None) -> None:
    if data is None:
        return
    blob = data.encode() if isinstance(data, str) else data
    if not blob:
        return
    with path.open("ab") as handle:
        handle.write(blob)
