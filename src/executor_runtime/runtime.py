# SPDX-License-Identifier: AGPL-3.0-or-later
"""ExecutorRuntime — dispatch by RxP runtime_kind.

Registers a ``RuntimeRunner`` per runtime_kind and routes each
invocation to the right runner. Default registry only contains
``SubprocessRunner`` for ``runtime_kind="subprocess"``; callers
inject additional runners (e.g. ``ManualRunner``, future
``HttpRunner``) at construction.

When an invocation arrives for a runtime_kind with no registered
runner, ExecutorRuntime returns a ``rejected`` RuntimeResult rather
than raising — same posture as the missing-working-directory check
in ``SubprocessRunner``.
"""
from __future__ import annotations

from datetime import UTC, datetime

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.io.json_io import write_result
from executor_runtime.runners.base import RuntimeRunner
from executor_runtime.runners.subprocess_runner import SubprocessRunner


class ExecutorRuntime:
    def __init__(
        self,
        *,
        runners: dict[str, RuntimeRunner] | None = None,
        runner: RuntimeRunner | None = None,
    ) -> None:
        """Construct a runtime.

        Pass ``runners`` (mapping of runtime_kind → runner) to register
        multiple kinds. Pass ``runner`` (legacy single-runner) to keep
        the pre-dispatch constructor working — it's treated as the
        subprocess runner.
        """
        if runners is not None:
            self._runners: dict[str, RuntimeRunner] = dict(runners)
        elif runner is not None:
            self._runners = {"subprocess": runner}
        else:
            self._runners = {"subprocess": SubprocessRunner()}

    @property
    def runner(self) -> RuntimeRunner:
        """Backwards-compat: pre-dispatch code reads ``runtime.runner``.
        Returns the subprocess runner if present, otherwise any one runner.
        """
        return self._runners.get("subprocess") or next(iter(self._runners.values()))

    def register(self, runtime_kind: str, runner: RuntimeRunner) -> None:
        """Register a runner for a runtime_kind."""
        self._runners[runtime_kind] = runner

    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        runner = self._runners.get(invocation.runtime_kind)
        if runner is None:
            return _rejected_no_runner(invocation)
        result = runner.run(invocation)
        if invocation.output_result_path:
            write_result(invocation.output_result_path, result)
        return result


def _rejected_no_runner(invocation: RuntimeInvocation) -> RuntimeResult:
    """Build a rejected RuntimeResult when no runner is registered."""
    now = datetime.now(UTC).isoformat()
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="rejected",
        exit_code=None,
        started_at=now,
        finished_at=now,
        stdout_path=None,
        stderr_path=None,
        artifacts=[],
        error_summary=f"no runner registered for runtime_kind={invocation.runtime_kind!r}",
    )
