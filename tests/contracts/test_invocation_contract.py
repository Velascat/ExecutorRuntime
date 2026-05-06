import pytest

from executor_runtime.contracts.invocation import RuntimeInvocation


def _base_invocation_kwargs() -> dict:
    return {
        "invocation_id": "inv-1",
        "runtime_name": "local",
        "working_directory": ".",
        "command": ["python", "-V"],
        "environment": {},
        "timeout_seconds": 30,
        "input_payload_path": None,
        "output_result_path": None,
        "artifact_directory": None,
    }


def test_rejects_empty_invocation_id() -> None:
    kwargs = _base_invocation_kwargs()
    kwargs["invocation_id"] = ""
    with pytest.raises(ValueError, match="invocation_id"):
        RuntimeInvocation(**kwargs)


def test_rejects_empty_runtime_name() -> None:
    kwargs = _base_invocation_kwargs()
    kwargs["runtime_name"] = ""
    with pytest.raises(ValueError, match="runtime_name"):
        RuntimeInvocation(**kwargs)


def test_rejects_empty_command() -> None:
    kwargs = _base_invocation_kwargs()
    kwargs["command"] = []
    with pytest.raises(ValueError, match="command"):
        RuntimeInvocation(**kwargs)


def test_rejects_non_positive_timeout() -> None:
    kwargs = _base_invocation_kwargs()
    kwargs["timeout_seconds"] = 0
    with pytest.raises(ValueError, match="timeout_seconds"):
        RuntimeInvocation(**kwargs)
