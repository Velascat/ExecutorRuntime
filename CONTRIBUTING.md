# Contributing to ExecutorRuntime

ExecutorRuntime is the runtime execution layer for RxP-style invocation requests. It executes normalized runtime invocations (subprocess execution, working directory control, environment overlay, timeout, stdout/stderr capture, exit-code normalization, artifact collection) and returns normalized runtime results.

## Before You Start

- Check open issues to avoid duplicate work
- For significant changes, open an issue first to discuss the approach
- All contributions must pass the test suite and linter before merging

## Development Setup

```bash
git clone https://github.com/ProtocolWarden/ExecutorRuntime.git
cd ExecutorRuntime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -q
```

## Linting

```bash
ruff check src/
```

## Scope Discipline

ExecutorRuntime intentionally has a narrow scope. Do **not** add:

- Schedulers, queues, or workflow orchestration
- Plugin systems or extension marketplaces
- Source/fork management (that lives in SourceRegistry)
- Routing decisions (that lives in SwitchBoard)
- Planning or proposal logic (that lives in OperationsCenter)
- Protocol/contract definitions (those live in RxP/CxRP)

If a feature requires reaching outside subprocess execution mechanics, it probably belongs in another repo.

## Adding a New Runner

`SubprocessRunner` is the v1 runner. New runners (e.g. container-based, remote SSH) should:

1. Implement the same input contract (`RuntimeInvocation`) and output contract (`RuntimeResult`)
2. Live behind a `Runner` protocol/abstract base
3. Ship with parity tests against `SubprocessRunner` for shared semantics
4. Document any deliberate behavior differences in the runner's own module docstring

## Pull Request Checklist

- [ ] Tests added for new behavior
- [ ] Existing tests still pass (`pytest -q`)
- [ ] Linter passes (`ruff check src/`)
- [ ] Public API changes are reflected in the README
- [ ] No silent failures introduced (errors surface as `RuntimeStatus` or raised exceptions, never swallowed)

## Code Style

- Type hints required on public functions
- Prefer dataclasses or frozen dataclasses for structured types
- No `from foo import *`
- Docstrings on public functions; comments only when the *why* is non-obvious
