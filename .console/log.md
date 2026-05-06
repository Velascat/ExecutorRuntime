# Log

_Chronological continuity log. Decisions, stop points, what changed and why._
_Not a task tracker — that's backlog.md. Keep entries concise and dated._

## Recent Decisions

_Log significant choices here so they survive context resets._

| Decision | Rationale | Date |
|----------|-----------|------|
| [what was decided] | [why] | [date] |

## Stop Points

- Phase 3a — RxP type adoption + process-group handling (2026-05-06, on `feat/rxp-types-and-process-group`): Killed ER's parallel dataclass copies of `RuntimeInvocation`/`RuntimeResult`/`RuntimeStatus`. Now re-exports the canonical RxP types (`from rxp.contracts import RuntimeInvocation, RuntimeResult, ArtifactDescriptor`); status is RxP's `runtime_status` vocabulary as string literals. Added rxp git dep. **SubprocessRunner upgraded** with kodo-equivalent process-group safety: `start_new_session=True` so child becomes process-group leader; on timeout, `os.killpg(SIGKILL)` reaps the entire group (prevents orphan claude/codex worker subprocesses); transient SIGTERM handler kills child group if supervising Python is killed (supervisor stop / OOM). `io/json_io.py` updated for pydantic (`model_validate` / `model_dump_json`). Tests updated: `runtime_kind` required everywhere; `RuntimeStatus` enum → string literals; new tests for unknown runtime_kind rejection + ArtifactDescriptor shape. 15 tests pass (+2). Phase 3b (OC integration) lands next on a separate branch in OperationsCenter.

## Notes

_Free-form scratch. Clear periodically — old entries can be deleted once no longer relevant._

---
