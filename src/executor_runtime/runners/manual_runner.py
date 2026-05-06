# SPDX-License-Identifier: AGPL-3.0-or-later
"""ManualRunner — delegate execution to a caller-supplied callable.

For runtimes that aren't a local subprocess: out-of-process services,
RPCs, message-queue dispatches, anything OC reaches across a boundary
the runtime layer doesn't directly own. The caller registers a
``dispatcher`` (any callable matching ``RuntimeRunner.run``); the
runner just forwards.

Use this when ``runtime_kind == "manual"`` on the invocation. Future
``HttpRunner`` / ``ContainerRunner`` will cover ``"http"`` /
``"container"`` with concrete implementations.
"""
from __future__ import annotations

from typing import Callable

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult


Dispatcher = Callable[[RuntimeInvocation], RuntimeResult]


class ManualRunner:
    """Forwards a RuntimeInvocation to a caller-supplied dispatcher.

    The dispatcher is responsible for honoring the runtime contract:
    same invocation_id, runtime_name, and runtime_kind echoed on the
    returned RuntimeResult. ManualRunner does not validate.
    """

    def __init__(self, dispatcher: Dispatcher) -> None:
        self._dispatcher = dispatcher

    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        return self._dispatcher(invocation)
