# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Velascat
"""Tests for AsyncHttpRunner — kickoff (202) + poll-until-terminal."""
from __future__ import annotations

import httpx

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.runners.async_http_runner import AsyncHttpRunner

KICKOFF_URL = "http://example.test/api/workflows/foo/run"
POLL_TEMPLATE = "http://example.test/api/workflows/runs/{run_id}"


def _invocation(metadata_extra: dict | None = None, **overrides) -> RuntimeInvocation:
    metadata = {
        "http.url": KICKOFF_URL,
        "http.poll_url_template": POLL_TEMPLATE,
        "http.poll_run_id_path": "run_id",
        "http.poll_status_path": "status",
        "http.poll_terminal_states": "completed,failed,cancelled",
        "http.poll_success_states": "completed",
        "http.poll_interval_seconds": "0.0",
    }
    if metadata_extra:
        metadata.update(metadata_extra)
    defaults = dict(
        invocation_id="inv-1",
        runtime_name="archon-workflow",
        runtime_kind="http_async",
        working_directory="/tmp",
        command=["unused"],
        environment={},
        timeout_seconds=10,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
        metadata=metadata,
    )
    defaults.update(overrides)
    return RuntimeInvocation(**defaults)


def _scripted_client(steps: list) -> httpx.Client:
    """Return an httpx.Client whose transport replays ``steps`` in order.

    Each step is either an ``httpx.Response`` (returned for that request) or an
    ``Exception`` (raised). The client cycles through steps on each call.
    """
    iterator = iter(steps)

    def _handler(request: httpx.Request) -> httpx.Response:
        nxt = next(iterator)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    return httpx.Client(transport=httpx.MockTransport(_handler))


def _make_runner(client: httpx.Client) -> AsyncHttpRunner:
    return AsyncHttpRunner(client=client, sleep=lambda *_: None)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_kickoff_then_poll_terminal_success(self):
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc123"}),  # kickoff
            httpx.Response(200, json={"status": "running"}),  # poll 1
            httpx.Response(200, json={"status": "completed"}),  # poll 2 (terminal)
        ])
        runner = _make_runner(client)
        result = runner.run(_invocation())
        assert result.status == "succeeded"
        assert result.exit_code == 0
        assert result.runtime_kind == "http_async"
        assert result.error_summary is None

    def test_kickoff_then_poll_terminal_failure(self):
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.Response(200, json={"status": "failed"}),
        ])
        runner = _make_runner(client)
        result = runner.run(_invocation())
        assert result.status == "failed"
        assert result.exit_code == 1
        assert "failed" in (result.error_summary or "")

    def test_terminal_status_in_alternate_field(self):
        client = _scripted_client([
            httpx.Response(202, json={"run": {"id": "abc"}}),
            httpx.Response(200, json={"run": {"status": "completed"}}),
        ])
        runner = _make_runner(client)
        inv = _invocation(metadata_extra={
            "http.poll_run_id_path": "run.id",
            "http.poll_status_path": "run.status",
        })
        result = runner.run(inv)
        assert result.status == "succeeded"

    def test_synchronous_200_response_treated_as_terminal(self):
        client = _scripted_client([
            httpx.Response(200, json={"status": "completed"}),
        ])
        runner = _make_runner(client)
        result = runner.run(_invocation())
        assert result.status == "succeeded"

    def test_synchronous_200_with_failure_status(self):
        client = _scripted_client([
            httpx.Response(200, json={"status": "failed"}),
        ])
        runner = _make_runner(client)
        result = runner.run(_invocation())
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# Validation / rejection
# ---------------------------------------------------------------------------


class TestRejection:
    def test_missing_kickoff_url(self):
        # Build a fresh metadata dict without http.url, no client needed (rejected first).
        inv = RuntimeInvocation(
            invocation_id="inv-1",
            runtime_name="rt",
            runtime_kind="http_async",
            working_directory="/tmp",
            command=["unused"],
            environment={},
            timeout_seconds=10,
            input_payload_path=None,
            output_result_path=None,
            artifact_directory=None,
            metadata={
                "http.poll_url_template": POLL_TEMPLATE,
                "http.poll_status_path": "status",
                "http.poll_terminal_states": "completed",
            },
        )
        client = _scripted_client([])
        result = _make_runner(client).run(inv)
        assert result.status == "rejected"
        assert "http.url" in (result.error_summary or "")

    def test_missing_poll_template(self):
        inv = _invocation()
        # Construct a fresh invocation lacking the template
        inv = RuntimeInvocation(**{
            **inv.model_dump(),
            "metadata": {k: v for k, v in inv.metadata.items() if k != "http.poll_url_template"},
        })
        result = _make_runner(_scripted_client([])).run(inv)
        assert result.status == "rejected"
        assert "poll_url_template" in (result.error_summary or "")

    def test_missing_status_path(self):
        inv = _invocation()
        inv = RuntimeInvocation(**{
            **inv.model_dump(),
            "metadata": {k: v for k, v in inv.metadata.items() if k != "http.poll_status_path"},
        })
        result = _make_runner(_scripted_client([])).run(inv)
        assert result.status == "rejected"
        assert "poll_status_path" in (result.error_summary or "")

    def test_missing_terminal_states(self):
        inv = _invocation()
        inv = RuntimeInvocation(**{
            **inv.model_dump(),
            "metadata": {k: v for k, v in inv.metadata.items() if k != "http.poll_terminal_states"},
        })
        result = _make_runner(_scripted_client([])).run(inv)
        assert result.status == "rejected"
        assert "poll_terminal_states" in (result.error_summary or "")

    def test_template_with_run_id_but_no_path(self):
        inv = _invocation()
        inv = RuntimeInvocation(**{
            **inv.model_dump(),
            "metadata": {k: v for k, v in inv.metadata.items() if k != "http.poll_run_id_path"},
        })
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
        ])
        result = _make_runner(client).run(inv)
        assert result.status == "rejected"
        assert "poll_run_id_path" in (result.error_summary or "")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestKickoffErrors:
    def test_non_202_kickoff_fails(self):
        client = _scripted_client([
            httpx.Response(500, text="boom"),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "500" in (result.error_summary or "")

    def test_kickoff_timeout(self):
        client = _scripted_client([
            httpx.TimeoutException("kickoff timed out"),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "kickoff" in (result.error_summary or "")

    def test_run_id_extraction_failure(self):
        client = _scripted_client([
            httpx.Response(202, json={"unexpected_field": "abc"}),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "no field at path" in (result.error_summary or "")


class TestPollErrors:
    def test_poll_non_200_fails(self):
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.Response(503, text="upstream down"),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "503" in (result.error_summary or "")

    def test_poll_timeout(self):
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.TimeoutException("poll timed out"),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "poll" in (result.error_summary or "")

    def test_status_extraction_failure(self):
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.Response(200, json={"unexpected": "missing status"}),
        ])
        result = _make_runner(client).run(_invocation())
        assert result.status == "failed"
        assert "no field at path" in (result.error_summary or "")


# ---------------------------------------------------------------------------
# Polling deadline / sleep wiring
# ---------------------------------------------------------------------------


class TestPollLoop:
    def test_sleep_called_between_polls(self):
        sleeps: list[float] = []
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.Response(200, json={"status": "running"}),
            httpx.Response(200, json={"status": "running"}),
            httpx.Response(200, json={"status": "completed"}),
        ])
        runner = AsyncHttpRunner(client=client, sleep=sleeps.append)
        inv = _invocation(metadata_extra={"http.poll_interval_seconds": "1.5"})
        result = runner.run(inv)
        assert result.status == "succeeded"
        # 3 polls, 2 sleeps between non-terminal results
        assert sleeps == [1.5, 1.5]

    def test_zero_interval_skips_sleep_arg(self):
        sleeps: list[float] = []
        client = _scripted_client([
            httpx.Response(202, json={"run_id": "abc"}),
            httpx.Response(200, json={"status": "running"}),
            httpx.Response(200, json={"status": "completed"}),
        ])
        runner = AsyncHttpRunner(client=client, sleep=sleeps.append)
        result = runner.run(_invocation())  # poll_interval=0.0 in default metadata
        assert result.status == "succeeded"
        assert sleeps == [0.0]
