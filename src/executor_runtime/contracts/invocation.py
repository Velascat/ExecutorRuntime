# SPDX-License-Identifier: AGPL-3.0-or-later
"""ExecutorRuntime consumes the canonical RxP RuntimeInvocation contract.

Re-exported here so callers can ``from executor_runtime.contracts
import RuntimeInvocation`` without depending on the RxP package
directly.
"""
from rxp.contracts import RuntimeInvocation

__all__ = ["RuntimeInvocation"]
