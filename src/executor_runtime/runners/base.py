# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
from typing import Protocol

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult


class RuntimeRunner(Protocol):
    def run(self, invocation: RuntimeInvocation) -> RuntimeResult: ...
