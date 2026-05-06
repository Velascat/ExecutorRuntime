# SPDX-License-Identifier: AGPL-3.0-or-later
"""HttpRunner — synchronous HTTP request/response runner.

For runtimes exposed as a synchronous HTTP endpoint (request → response,
no polling, no streaming). Pairs with ``runtime_kind="http"``.

Wire shape (carried via RuntimeInvocation.metadata):
  - ``http.method``: GET / POST / PUT / etc. (default POST)
  - ``http.url``: absolute URL the runner will hit
  - ``http.body_format``: "json" (default) or "form"

The body is built from ``RuntimeInvocation.metadata['http.body']`` if
present (string) or auto-derived from the invocation otherwise. For
async APIs (202 + poll/stream), don't use this runner — write a
backend-specific dispatcher and use ManualRunner instead.

This runner installs no global state. Each ``run`` opens a short-lived
``httpx.Client`` so timeout/cancellation semantics are local to the call.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover - dep is optional
    httpx = None  # type: ignore[assignment]

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult


class HttpRunner:
    """Generic synchronous HTTP runner.

    Construction params:
      - ``follow_redirects`` (default True)
      - ``verify`` (default True — TLS verification)
      - ``client``: a pre-built ``httpx.Client``; tests inject mocks here.
    """

    def __init__(
        self,
        *,
        follow_redirects: bool = True,
        verify: bool = True,
        client: Any = None,
    ) -> None:
        if httpx is None and client is None:
            raise ImportError(
                "HttpRunner requires httpx. Install with "
                "`pip install executor-runtime[http]`"
            )
        self._follow_redirects = follow_redirects
        self._verify = verify
        self._client = client

    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        started = _utc_now_iso()
        meta = invocation.metadata or {}

        url = meta.get("http.url")
        if not url:
            return _rejected(invocation, started, "missing metadata['http.url']")

        method = (meta.get("http.method") or "POST").upper()
        body_format = meta.get("http.body_format") or "json"
        body_raw = meta.get("http.body")

        try:
            content_kw = _build_content_kwargs(body_raw, body_format)
        except ValueError as exc:
            return _rejected(invocation, started, f"invalid body: {exc}")

        timeout = invocation.timeout_seconds

        client = self._client
        owns_client = False
        if client is None:
            client = httpx.Client(
                follow_redirects=self._follow_redirects,
                verify=self._verify,
                timeout=timeout,
            )
            owns_client = True

        try:
            try:
                response = client.request(method, url, **content_kw)
            except httpx.TimeoutException as exc:  # type: ignore[union-attr]
                return _timed_out(invocation, started, timeout, exc)
            except Exception as exc:  # network errors, dns, etc.
                return _failed(invocation, started, f"http error: {exc}")
        finally:
            if owns_client:
                client.close()

        finished = _utc_now_iso()
        status = "succeeded" if 200 <= response.status_code < 300 else "failed"
        error_summary = None
        if status == "failed":
            preview = response.text[:200] if response.text else ""
            error_summary = f"HTTP {response.status_code}: {preview}".strip()

        return RuntimeResult(
            invocation_id=invocation.invocation_id,
            runtime_name=invocation.runtime_name,
            runtime_kind=invocation.runtime_kind,
            status=status,
            exit_code=response.status_code,
            started_at=started,
            finished_at=finished,
            stdout_path=None,
            stderr_path=None,
            artifacts=[],
            error_summary=error_summary,
        )


def _build_content_kwargs(body_raw: str | None, body_format: str) -> dict[str, Any]:
    if body_raw is None:
        return {}
    if body_format == "json":
        try:
            payload = json.loads(body_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"http.body is not valid JSON: {exc}") from exc
        return {"json": payload}
    if body_format == "form":
        try:
            payload = json.loads(body_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"http.body is not valid form JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("http.body for form must be a JSON object")
        return {"data": payload}
    raise ValueError(f"unknown body_format: {body_format!r}")


def _rejected(invocation: RuntimeInvocation, started: str, reason: str) -> RuntimeResult:
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="rejected",
        exit_code=None,
        started_at=started,
        finished_at=_utc_now_iso(),
        stdout_path=None,
        stderr_path=None,
        artifacts=[],
        error_summary=reason,
    )


def _failed(invocation: RuntimeInvocation, started: str, reason: str) -> RuntimeResult:
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="failed",
        exit_code=None,
        started_at=started,
        finished_at=_utc_now_iso(),
        stdout_path=None,
        stderr_path=None,
        artifacts=[],
        error_summary=reason,
    )


def _timed_out(
    invocation: RuntimeInvocation,
    started: str,
    timeout: int | None,
    exc: Exception,
) -> RuntimeResult:
    note = f"http request exceeded timeout of {timeout}s" if timeout else "http request timed out"
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="timed_out",
        exit_code=None,
        started_at=started,
        finished_at=_utc_now_iso(),
        stdout_path=None,
        stderr_path=None,
        artifacts=[],
        error_summary=f"{note}: {exc}",
    )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
