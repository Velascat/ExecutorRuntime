# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for HttpRunner — synchronous HTTP request/response runner."""
import json

import httpx
import pytest

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.runners.http_runner import HttpRunner


def _invocation(**overrides) -> RuntimeInvocation:
    metadata = {"http.url": "http://example.test/api/health"}
    metadata.update(overrides.pop("metadata", {}))
    defaults = dict(
        invocation_id="inv-1",
        runtime_name="example",
        runtime_kind="http",
        working_directory="/tmp",
        command=["http"],
        environment={},
        timeout_seconds=10,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
        metadata=metadata,
    )
    defaults.update(overrides)
    return RuntimeInvocation(**defaults)


def _stub_client(*, response: httpx.Response | None = None,
                 raises: Exception | None = None) -> httpx.Client:
    """Build an httpx.Client that returns / raises the configured outcome."""

    def _handler(request: httpx.Request) -> httpx.Response:
        if raises is not None:
            raise raises
        return response or httpx.Response(200, json={"status": "ok"})

    return httpx.Client(transport=httpx.MockTransport(_handler))


class TestHappyPath:
    def test_2xx_returns_succeeded(self):
        client = _stub_client(response=httpx.Response(200, json={"ok": True}))
        runner = HttpRunner(client=client)
        result = runner.run(_invocation())
        assert result.status == "succeeded"
        assert result.exit_code == 200

    def test_runtime_kind_is_echoed(self):
        client = _stub_client()
        runner = HttpRunner(client=client)
        inv = _invocation()
        result = runner.run(inv)
        assert result.runtime_kind == "http"
        assert result.invocation_id == inv.invocation_id

    def test_default_method_is_post(self):
        seen: list[str] = []

        def _handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.method)
            return httpx.Response(200)

        client = httpx.Client(transport=httpx.MockTransport(_handler))
        HttpRunner(client=client).run(_invocation())
        assert seen == ["POST"]

    def test_explicit_method_via_metadata(self):
        seen: list[str] = []

        def _handler(request):
            seen.append(request.method)
            return httpx.Response(200)

        client = httpx.Client(transport=httpx.MockTransport(_handler))
        inv = _invocation(metadata={
            "http.url": "http://example.test/api/health",
            "http.method": "GET",
        })
        HttpRunner(client=client).run(inv)
        assert seen == ["GET"]

    def test_json_body_sent_through(self):
        seen: list[bytes] = []

        def _handler(request):
            seen.append(request.content)
            return httpx.Response(200)

        client = httpx.Client(transport=httpx.MockTransport(_handler))
        inv = _invocation(metadata={
            "http.url": "http://example.test/run",
            "http.body": json.dumps({"task": "hello"}),
        })
        HttpRunner(client=client).run(inv)
        assert json.loads(seen[0]) == {"task": "hello"}


class TestFailurePaths:
    def test_4xx_returns_failed(self):
        client = _stub_client(response=httpx.Response(400, text="bad request"))
        result = HttpRunner(client=client).run(_invocation())
        assert result.status == "failed"
        assert result.exit_code == 400
        assert "HTTP 400" in (result.error_summary or "")

    def test_5xx_returns_failed(self):
        client = _stub_client(response=httpx.Response(503, text="service unavailable"))
        result = HttpRunner(client=client).run(_invocation())
        assert result.status == "failed"
        assert result.exit_code == 503

    def test_missing_url_returns_rejected(self):
        client = _stub_client()
        # Build an invocation directly without the default http.url metadata.
        inv = RuntimeInvocation(
            invocation_id="inv-no-url", runtime_name="x", runtime_kind="http",
            working_directory="/tmp", command=["x"], environment={},
            timeout_seconds=10, input_payload_path=None, output_result_path=None,
            artifact_directory=None, metadata={},
        )
        result = HttpRunner(client=client).run(inv)
        assert result.status == "rejected"
        assert "http.url" in (result.error_summary or "")

    def test_invalid_body_json_returns_rejected(self):
        client = _stub_client()
        inv = _invocation(metadata={
            "http.url": "http://example.test/run",
            "http.body": "{not-json",
        })
        result = HttpRunner(client=client).run(inv)
        assert result.status == "rejected"
        assert "invalid body" in (result.error_summary or "")

    def test_unknown_body_format_returns_rejected(self):
        client = _stub_client()
        inv = _invocation(metadata={
            "http.url": "http://example.test/run",
            "http.body": "{}",
            "http.body_format": "telepathy",
        })
        result = HttpRunner(client=client).run(inv)
        assert result.status == "rejected"

    def test_timeout_returns_timed_out(self):
        client = _stub_client(raises=httpx.ReadTimeout("timed out"))
        result = HttpRunner(client=client).run(_invocation())
        assert result.status == "timed_out"
        assert "timeout" in (result.error_summary or "").lower()

    def test_network_error_returns_failed(self):
        client = _stub_client(raises=httpx.ConnectError("dns failure"))
        result = HttpRunner(client=client).run(_invocation())
        assert result.status == "failed"
        assert "http error" in (result.error_summary or "").lower()


class TestImportGuard:
    def test_construction_without_httpx_raises_when_no_client(self, monkeypatch):
        """If httpx is missing and no client is injected, the constructor errors."""
        import executor_runtime.runners.http_runner as mod
        monkeypatch.setattr(mod, "httpx", None)
        with pytest.raises(ImportError, match="executor-runtime\\[http\\]"):
            HttpRunner()
