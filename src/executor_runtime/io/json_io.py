import json
from pathlib import Path

from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult


def read_invocation(path: str) -> RuntimeInvocation:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return RuntimeInvocation.model_validate(payload)


def write_result(path: str, result: RuntimeResult) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
