from executor_runtime.contracts.invocation import RuntimeInvocation
from executor_runtime.contracts.result import RuntimeResult
from executor_runtime.io.json_io import write_result
from executor_runtime.runners.base import RuntimeRunner
from executor_runtime.runners.subprocess_runner import SubprocessRunner


class ExecutorRuntime:
    def __init__(self, runner: RuntimeRunner | None = None):
        self.runner = runner or SubprocessRunner()

    def run(self, invocation: RuntimeInvocation) -> RuntimeResult:
        result = self.runner.run(invocation)
        if invocation.output_result_path:
            write_result(invocation.output_result_path, result)
        return result
