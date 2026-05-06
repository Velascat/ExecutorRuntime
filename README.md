# ExecutorRuntime

`ExecutorRuntime` is the runtime execution layer for RxP-style invocation requests. It executes normalized runtime invocations and returns normalized runtime results.

## What this repo is

This repository focuses on local execution concerns:

- subprocess execution
- command execution from normalized invocation inputs
- working directory control
- environment overlay handling
- timeout handling
- stdout/stderr capture
- exit-code normalization
- artifact path collection
- result JSON output helpers

## What this repo is not

This repository is not:

- OperationsCenter
- SwitchBoard
- SourceRegistry
- CxRP
- a scheduler
- a queue system
- a fork manager
- a plugin marketplace

## First supported runner

v1 supports a single runner: `SubprocessRunner`.

## Example usage

```python
from executor_runtime import ExecutorRuntime
from executor_runtime.contracts.invocation import RuntimeInvocation

runtime = ExecutorRuntime()

result = runtime.run(
    RuntimeInvocation(
        invocation_id="example-001",
        runtime_name="local-echo",
        working_directory=".",
        command=["python", "-c", "print('hello from runtime')"],
        environment={},
        timeout_seconds=30,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
    )
)

print(result.status)
```
