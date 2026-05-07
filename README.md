# ExecutorRuntime

`ExecutorRuntime` is the generic runtime execution layer for [RxP](https://github.com/Velascat/RxP)-shaped invocations. It dispatches by `runtime_kind` to a registered runner and returns a normalized RxP `RuntimeResult`.

```text
RuntimeInvocation → ExecutorRuntime.run → RuntimeResult
                       ├─ "subprocess" → SubprocessRunner
                       ├─ "manual"     → ManualRunner (caller-supplied dispatcher)
                       └─ "http"       → HttpRunner   (sync request/response)
```

## What this repo is

Generic runtime mechanics:

- subprocess execution with process-group safety (`start_new_session=True`, `os.killpg(SIGKILL)` on timeout, transient SIGTERM handler)
- environment overlay
- working directory control
- timeout enforcement
- stdout/stderr capture to files
- exit-code normalization
- ArtifactDescriptor collection
- dispatch-by-`runtime_kind` registry

## What this repo is not

- OperationsCenter — orchestration, planning, policy
- SwitchBoard — lane/backend selection
- SourceRegistry — source/fork/dependency tracking
- CxRP — orchestration contract
- a scheduler / queue system / fork manager / agent framework

## Runners (available in v0.1)

| Runner | runtime_kind | What it does |
|---|---|---|
| `SubprocessRunner` | `subprocess` | Local subprocess with process-group safety. Default registered runner. |
| `ManualRunner` | `manual` | Forwards invocation to a caller-supplied dispatcher callable. For out-of-process services where ExecutorRuntime doesn't own the transport. |
| `HttpRunner` | `http` | Synchronous HTTP request/response. URL/method/body read from `RuntimeInvocation.metadata`. |

Async-shaped HTTP APIs (202 + poll/stream) are deferred — see backlog.

## Example usage

### Subprocess (default)

```python
from executor_runtime import ExecutorRuntime
from executor_runtime.contracts import RuntimeInvocation

runtime = ExecutorRuntime()  # SubprocessRunner registered for "subprocess"

result = runtime.run(
    RuntimeInvocation(
        invocation_id="example-001",
        runtime_name="local-echo",
        runtime_kind="subprocess",
        working_directory=".",
        command=["python", "-c", "print('hello')"],
        environment={},
        timeout_seconds=30,
        input_payload_path=None,
        output_result_path=None,
        artifact_directory=None,
        metadata={},
    )
)
print(result.status)  # "succeeded"
```

### Manual (out-of-process service)

```python
from executor_runtime import ExecutorRuntime
from executor_runtime.runners import ManualRunner

def my_dispatcher(invocation):
    # Your code: HTTP call, queue publish, RPC, whatever
    raw = call_external_service(...)
    return synthesize_runtime_result(invocation, raw)

runtime = ExecutorRuntime()
runtime.register("manual", ManualRunner(my_dispatcher))

result = runtime.run(invocation_with_kind_manual)
```

### HTTP (synchronous)

```python
from executor_runtime import ExecutorRuntime
from executor_runtime.runners import HttpRunner

runtime = ExecutorRuntime()
runtime.register("http", HttpRunner())

# Invocation metadata carries http.url + http.method + http.body
result = runtime.run(invocation_with_runtime_kind_http)
```

## Installation

```bash
pip install executor-runtime
# or with HTTP support:
pip install "executor-runtime[http]"
```

For development:

```bash
git clone https://github.com/Velascat/ExecutorRuntime.git
cd ExecutorRuntime
pip install -e ".[dev,http]"
pytest -q
```

## Contracts

ExecutorRuntime consumes RxP types directly — no parallel dataclasses:

```python
from rxp.contracts import RuntimeInvocation, RuntimeResult, ArtifactDescriptor
```

See [RxP](https://github.com/Velascat/RxP) for the contract definitions.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
