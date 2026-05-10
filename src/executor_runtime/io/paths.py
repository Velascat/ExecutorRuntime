# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation


def capture_directory(invocation: RuntimeInvocation) -> Path:
    base = (
        Path(invocation.artifact_directory)
        if invocation.artifact_directory
        else Path(invocation.working_directory) / ".executor_runtime"
    )
    return base / invocation.invocation_id
