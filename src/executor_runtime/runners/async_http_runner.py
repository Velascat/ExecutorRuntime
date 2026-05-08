# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Velascat
"""AsyncHttpRunner — kickoff (202) + poll-until-terminal HTTP runner.

For runtimes that kick off work via an HTTP endpoint and surface
completion through a *separate* status URL. Pairs with
``runtime_kind="http_async"``.

Wire shape (carried via ``RuntimeInvocation.metadata`` — strings only,
matching RxP metadata typing):

  Kickoff (same as HttpRunner):
    - ``http.url``                  : kickoff URL (POST endpoint)
    - ``http.method``               : usually POST (default POST)
    - ``http.body_format``          : ``json`` (default) or ``form``
    - ``http.body``                 : kickoff request body, JSON-encoded string

  Poll loop (new):
    - ``http.poll_url_template``    : status URL template, with
                                      ``{run_id}`` to be substituted from the
                                      kickoff response. Required.
    - ``http.poll_run_id_path``     : dotted path into the kickoff response
                                      JSON to extract run_id, e.g. ``run_id``
                                      or ``data.run.id``. Required when the
                                      template contains ``{run_id}``.
    - ``http.poll_status_path``     : dotted path into each poll response
                                      JSON to extract status, e.g.
                                      ``status`` or ``run.status``. Required.
    - ``http.poll_terminal_states`` : comma-separated list of terminal
                                      statuses (e.g. ``completed,failed,cancelled``).
                                      Required.
    - ``http.poll_success_states``  : comma-separated subset of terminal
                                      states meaning success (default:
                                      ``completed``).
    - ``http.poll_interval_seconds``: seconds between polls (default ``2.0``).
    - ``http.poll_pending_codes``   : comma-separated list of HTTP codes that
                                      mean "still pending, keep polling"
                                      (e.g. ``404`` for backends that 404
                                      until the run is registered). Default
                                      empty (only 200 is accepted; everything
                                      else fails the poll loop).

Kickoff status codes:
  - ``202``: standard async accept; proceed to poll loop.
  - ``200``: if the response body carries a status at ``poll_status_path``
            whose value is in ``poll_terminal_states``, the kickoff is
            treated as a synchronous terminal result. Otherwise the 200 is
            treated as kickoff acknowledgement and the poll loop runs.
            (Some backends, e.g. Archon, return 200 with a non-terminal
            status like ``"started"`` to acknowledge dispatch.)
  - everything else: failure.

Sync from the caller's POV: ``run()`` blocks until a terminal status is
observed or the invocation timeout elapses. For genuinely concurrent
async needs the caller can run multiple invocations on threads — the
runner is reentrant.

Each call uses a short-lived ``httpx.Client``; no global state.
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover - dep is optional
    httpx = None  # type: ignore[assignment]

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult

_DEFAULT_POLL_INTERVAL = 2.0
_DEFAULT_SUCCESS_STATES = ("completed",)


class AsyncHttpRunner:
    """Generic async-shaped HTTP runner.

    Construction params (mirror HttpRunner where applicable):
      - ``follow_redirects`` (default True)
      - ``verify`` (default True — TLS verification)
      - ``client``: a pre-built ``httpx.Client``; tests inject mocks here.
      - ``sleep``: callable used between polls. Defaults to ``time.sleep``;
                  tests pass a no-op or a counter to drive the loop.
    """

    def __init__(
        self,
        *,
        follow_redirects: bool = True,
        verify: bool = True,
        client: Any = None,
        sleep: Any = None,
    ) -> None:
        if httpx is None and client is None:
            raise ImportError(
                "AsyncHttpRunner requires httpx. Install with "
                "`pip install executor-runtime[http]`"
            )
        self._follow_redirects = follow_redirects
        self._verify = verify
        self._client = client
        self._sleep = sleep or time.sleep

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        started = _utc_now_iso()
        meta = invocation.metadata or {}

        kickoff_url = meta.get("http.url")
        if not kickoff_url:
            return _rejected(invocation, started, "missing metadata['http.url']")

        poll_url_template = meta.get("http.poll_url_template")
        if not poll_url_template:
            return _rejected(invocation, started, "missing metadata['http.poll_url_template']")

        poll_status_path = meta.get("http.poll_status_path")
        if not poll_status_path:
            return _rejected(invocation, started, "missing metadata['http.poll_status_path']")

        terminal_raw = meta.get("http.poll_terminal_states")
        if not terminal_raw:
            return _rejected(invocation, started, "missing metadata['http.poll_terminal_states']")
        terminal_states = tuple(s.strip() for s in terminal_raw.split(",") if s.strip())
        if not terminal_states:
            return _rejected(invocation, started, "metadata['http.poll_terminal_states'] is empty")

        success_raw = meta.get("http.poll_success_states") or ",".join(_DEFAULT_SUCCESS_STATES)
        success_states = tuple(s.strip() for s in success_raw.split(",") if s.strip())

        pending_raw = meta.get("http.poll_pending_codes") or ""
        try:
            pending_codes = tuple(
                int(s.strip()) for s in pending_raw.split(",") if s.strip()
            )
        except ValueError:
            return _rejected(
                invocation, started,
                "http.poll_pending_codes must be comma-separated integers",
            )

        poll_interval = _parse_float(meta.get("http.poll_interval_seconds"), _DEFAULT_POLL_INTERVAL)
        if poll_interval < 0:
            return _rejected(invocation, started, "poll_interval_seconds must be non-negative")

        kickoff_method = (meta.get("http.method") or "POST").upper()
        body_format = meta.get("http.body_format") or "json"
        body_raw = meta.get("http.body")
        try:
            content_kw = _build_content_kwargs(body_raw, body_format)
        except ValueError as exc:
            return _rejected(invocation, started, f"invalid body: {exc}")

        timeout = invocation.timeout_seconds
        deadline_monotonic = _deadline(timeout)

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
            # ── Kickoff ───────────────────────────────────────────────
            try:
                kickoff_resp = client.request(kickoff_method, kickoff_url, **content_kw)
            except httpx.TimeoutException as exc:  # type: ignore[union-attr]
                return _timed_out(invocation, started, timeout, exc, "kickoff")
            except Exception as exc:  # pragma: no cover - dns/network
                return _failed(invocation, started, f"kickoff http error: {exc}")

            if kickoff_resp.status_code == 200:
                # 200 has two modes:
                #  - server returned a synchronous terminal result (status
                #    field present and in terminal_states)
                #  - server acknowledged async dispatch (status field absent
                #    or non-terminal, e.g. Archon's {accepted, status:"started"})
                if _is_synchronous_terminal(
                    kickoff_resp, poll_status_path, terminal_states,
                ):
                    return _terminal_from_kickoff(
                        invocation, started, kickoff_resp,
                        success_states, poll_status_path,
                    )
                # Fall through to poll loop — kickoff was an ack, not a result.
            elif kickoff_resp.status_code != 202:
                preview = kickoff_resp.text[:200] if kickoff_resp.text else ""
                msg = (
                    f"kickoff expected 202 (or 200), got HTTP "
                    f"{kickoff_resp.status_code}: {preview}"
                ).strip()
                return _failed(invocation, started, msg)

            # ── Poll URL construction ────────────────────────────────
            poll_url = poll_url_template
            if "{run_id}" in poll_url:
                run_id_path = meta.get("http.poll_run_id_path")
                if not run_id_path:
                    return _rejected(
                        invocation, started,
                        "poll_url_template contains {run_id} but no poll_run_id_path provided",
                    )
                try:
                    kickoff_payload = kickoff_resp.json()
                except json.JSONDecodeError as exc:
                    return _failed(invocation, started, f"kickoff response is not JSON: {exc}")
                run_id = _extract_path(kickoff_payload, run_id_path)
                if run_id is None:
                    msg = (
                        f"kickoff response has no field at path "
                        f"{run_id_path!r}: {kickoff_payload!r}"
                    )
                    return _failed(invocation, started, msg)
                poll_url = poll_url.replace("{run_id}", str(run_id))

            # ── Poll loop ────────────────────────────────────────────
            while True:
                if _deadline_exceeded(deadline_monotonic):
                    return _timed_out(
                        invocation, started, timeout,
                        TimeoutError("poll loop deadline exceeded"),
                        "poll",
                    )

                try:
                    poll_resp = client.get(poll_url)
                except httpx.TimeoutException as exc:  # type: ignore[union-attr]
                    return _timed_out(invocation, started, timeout, exc, "poll")
                except Exception as exc:  # pragma: no cover - dns/network
                    return _failed(invocation, started, f"poll http error: {exc}")

                if poll_resp.status_code != 200:
                    if poll_resp.status_code in pending_codes:
                        # Backend reports "still pending" with this code (e.g.
                        # Archon's 404 before the run is registered to a
                        # worker). Sleep and poll again.
                        self._sleep(poll_interval)
                        continue
                    preview = poll_resp.text[:200] if poll_resp.text else ""
                    return _failed(
                        invocation, started,
                        f"poll expected HTTP 200, got {poll_resp.status_code}: {preview}".strip(),
                    )
                try:
                    poll_payload = poll_resp.json()
                except json.JSONDecodeError as exc:
                    return _failed(invocation, started, f"poll response is not JSON: {exc}")

                status = _extract_path(poll_payload, poll_status_path)
                if status is None:
                    msg = (
                        f"poll response has no field at path "
                        f"{poll_status_path!r}: {poll_payload!r}"
                    )
                    return _failed(invocation, started, msg)
                status_str = str(status)
                if status_str in terminal_states:
                    finished = _utc_now_iso()
                    success = status_str in success_states
                    return RuntimeResult(
                        invocation_id=invocation.invocation_id,
                        runtime_name=invocation.runtime_name,
                        runtime_kind=invocation.runtime_kind,
                        status="succeeded" if success else "failed",
                        exit_code=0 if success else 1,
                        started_at=started,
                        finished_at=finished,
                        stdout_path=None,
                        stderr_path=None,
                        artifacts=[],
                        error_summary=(
                            None if success
                            else f"backend reported terminal status: {status_str}"
                        ),
                    )

                # Not terminal — wait and poll again.
                self._sleep(poll_interval)
        finally:
            if owns_client:
                client.close()


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


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


def _extract_path(data: Any, dotted_path: str) -> Any:
    """Walk a dotted path through nested dicts; returns None if any segment misses."""
    cur = data
    for seg in dotted_path.split("."):
        if not seg:
            continue
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None
    return cur


def _parse_float(raw: str | None, default: float) -> float:
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _deadline(timeout_seconds: int | None) -> float | None:
    if timeout_seconds is None:
        return None
    return time.monotonic() + float(timeout_seconds)


def _deadline_exceeded(deadline_monotonic: float | None) -> bool:
    if deadline_monotonic is None:
        return False
    return time.monotonic() >= deadline_monotonic


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_synchronous_terminal(
    response: Any,
    poll_status_path: str,
    terminal_states: tuple[str, ...],
) -> bool:
    """Inspect a 200 kickoff response to decide if it's a sync terminal result.

    The kickoff path treats 200 as "synchronous result" only when the response
    body carries a status at ``poll_status_path`` whose value appears in
    ``terminal_states``. Otherwise the 200 is interpreted as kickoff
    acknowledgement and the caller proceeds to the poll loop.

    Returns False on any parse error (treat as kickoff ack — let the poll
    loop deal with it).
    """
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return False
    status = _extract_path(payload, poll_status_path)
    if status is None:
        return False
    return str(status) in terminal_states


def _terminal_from_kickoff(
    invocation: RuntimeInvocation,
    started: str,
    response: Any,
    success_states: tuple[str, ...],
    poll_status_path: str,
) -> RuntimeResult:
    """Build a RuntimeResult when the kickoff returned 200 (synchronous response).

    Treats the response body as already-terminal — extracts status using the
    same path the poll loop would have used.
    """
    finished = _utc_now_iso()
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        return _failed(invocation, started, f"sync 200 response is not JSON: {exc}")
    status = _extract_path(payload, poll_status_path)
    success = status is not None and str(status) in success_states
    return RuntimeResult(
        invocation_id=invocation.invocation_id,
        runtime_name=invocation.runtime_name,
        runtime_kind=invocation.runtime_kind,
        status="succeeded" if success else "failed",
        exit_code=0 if success else 1,
        started_at=started,
        finished_at=finished,
        stdout_path=None,
        stderr_path=None,
        artifacts=[],
        error_summary=None if success else f"sync 200 reported non-success status: {status}",
    )


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
    phase: str,
) -> RuntimeResult:
    note = (
        f"{phase} exceeded timeout of {timeout}s: {exc}"
        if timeout
        else f"{phase} timed out: {exc}"
    )
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
        error_summary=note,
    )
