# SPDX-License-Identifier: AGPL-3.0-or-later
"""Default RuntimeRunner implementation — subprocess execution.

Important behavior:
- Spawns the child in a fresh process session (``start_new_session=True``)
  so it becomes the leader of its own process group.
- On timeout, kills the **entire group** via ``os.killpg(SIGKILL)``.
  This reaps any descendants (e.g. orchestrator-spawned worker
  processes) that would otherwise become orphans and continue
  consuming CPU / API quota.
- Installs a transient SIGTERM handler so that if the supervising
  Python process is itself killed (supervisor stop, OOM killer), the
  child group is killed before exit. The previous SIGTERM handler is
  restored on return.

stdout and stderr are captured to files inside ``capture_directory``
so they can be referenced as ``ArtifactDescriptor`` paths in the
returned ``RuntimeResult``.
"""
from __future__ import annotations

import os
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import ArtifactDescriptor, RuntimeResult
from executor_runtime.io.paths import capture_directory


class SubprocessRunner:
    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        started_at = _utc_now_iso()
        working_dir = Path(invocation.working_directory)
        if not working_dir.exists() or not working_dir.is_dir():
            return RuntimeResult(
                invocation_id=invocation.invocation_id,
                runtime_name=invocation.runtime_name,
                runtime_kind=invocation.runtime_kind,
                status="rejected",
                exit_code=None,
                started_at=started_at,
                finished_at=_utc_now_iso(),
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

        status, exit_code, error_summary = _run_with_process_group(
            invocation=invocation,
            working_dir=working_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            env=env,
        )

        finished_at = _utc_now_iso()
        artifacts = [
            ArtifactDescriptor(
                artifact_id="stdout",
                path=str(stdout_path),
                kind="log_excerpt",
                description="captured stdout",
            ),
            ArtifactDescriptor(
                artifact_id="stderr",
                path=str(stderr_path),
                kind="log_excerpt",
                description="captured stderr",
            ),
        ]

        return RuntimeResult(
            invocation_id=invocation.invocation_id,
            runtime_name=invocation.runtime_name,
            runtime_kind=invocation.runtime_kind,
            status=status,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            artifacts=artifacts,
            error_summary=error_summary,
        )


def _run_with_process_group(
    *,
    invocation: RuntimeInvocation,
    working_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str],
) -> tuple[str, int | None, str | None]:
    """Run the subprocess as a process-group leader and reap on timeout.

    Returns ``(status, exit_code, error_summary)``.
    """
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc = subprocess.Popen(
            list(invocation.command),
            cwd=working_dir,
            env=env,
            stdout=out_f,
            stderr=err_f,
            shell=False,
            start_new_session=True,
        )

        try:
            pgid: int | None = os.getpgid(proc.pid) if proc.pid else None
        except OSError:
            pgid = None

        def _kill_group() -> None:
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass

        prev_sigterm = signal.getsignal(signal.SIGTERM)

        def _sigterm_handler(signum: int, _frame: object) -> NoReturn:
            _kill_group()
            signal.signal(signal.SIGTERM, prev_sigterm)
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGTERM, _sigterm_handler)
        try:
            try:
                exit_code = proc.wait(timeout=invocation.timeout_seconds)
            except subprocess.TimeoutExpired:
                _kill_group()
                try:
                    exit_code = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    exit_code = None
                error_summary = (
                    f"process exceeded timeout of {invocation.timeout_seconds} seconds"
                    if invocation.timeout_seconds
                    else "process timed out"
                )
                return "timed_out", exit_code, error_summary
        finally:
            signal.signal(signal.SIGTERM, prev_sigterm)

    status = "succeeded" if exit_code == 0 else "failed"
    return status, exit_code, None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
