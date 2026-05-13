# Log

_Chronological continuity log. Decisions, stop points, what changed and why._
_Not a task tracker — that's backlog.md. Keep entries concise and dated._

- 2026-05-12 — RepoGraph boundary artifact wiring tightened to file-only: the
  custodian audit path now materializes `REPOGRAPH_BOUNDARY_ARTIFACT_FILE` from a
  source locator before invoking Custodian, and the remaining deployment-facing
  templates were aligned to `PlatformDeployment` naming.

## Recent Decisions

- Wire cross_repo config (2026-05-08, on chore/wire-cross-repo-config): Added `audit.cross_repo.platform_manifest_repo: ../PlatformManifest` to `.custodian/config.yaml`. Enables X1/X2/X3 detectors; live run shows 0 findings.

| Decision | Rationale | Date |
|----------|-----------|------|
| [what was decided] | [why] | [date] |

## Stop Points

- HttpRunner — synchronous request/response (2026-05-06, on `feat/http-runner`): New `HttpRunner` covers `runtime_kind="http"`. Reads URL/method/body from `RuntimeInvocation.metadata` (`http.url`, `http.method` default POST, `http.body` JSON, `http.body_format` json/form). 2xx → succeeded, 4xx/5xx → failed (with HTTP-status preview in `error_summary`), `httpx.TimeoutException` → timed_out, network errors → failed, missing URL or invalid body → rejected. Synchronous request-response only — async APIs (202+poll/stream like Archon's) need a backend-specific dispatcher via `ManualRunner`. New `[http]` extras_require pulls in httpx; runner raises ImportError at construction if httpx missing AND no client is injected (test seam). 38 tests pass (+13 across `tests/runners/test_http_runner.py`).

## Backlog

- **Async HTTP runner support** — current `HttpRunner` is request-response only. Backends with async APIs (Archon's `POST /api/workflows/{name}/run` returns 202; results come via polling `/api/workflows/runs/{runId}` or SSE `/api/stream/{conversationId}`) can't use it as-is. Decision before designing: add `AsyncHttpRunner` with poll-or-stream completion semantics, OR keep async dispatching in backend-specific `ManualRunner` dispatchers (the current archon Phase 3 path).

- Dispatch-by-runtime_kind + ManualRunner (2026-05-06, on `feat/dispatch-by-runtime-kind`): ExecutorRuntime now routes invocations to a registered runner by `runtime_kind` instead of using a single hardcoded runner. Default registry contains `SubprocessRunner` for `runtime_kind="subprocess"`; new `ManualRunner` wraps a caller-supplied dispatcher callable for `runtime_kind="manual"` (out-of-process services that OC dispatches to without owning the transport — archon's case). Constructor accepts `runners=` (dict[kind, Runner]) for multi-kind setups; legacy `runner=` kwarg still works (treated as the subprocess runner). New `register(kind, runner)` for late binding. Unregistered kinds return a `rejected` RuntimeResult with `error_summary="no runner registered for runtime_kind=..."` rather than raising. Future http/container runners drop in via the same mechanism. 25 tests pass (+10 new across `test_manual_runner.py` and `test_dispatch.py`).

- Phase 3a — RxP type adoption + process-group handling (2026-05-06, on `feat/rxp-types-and-process-group`): Killed ER's parallel dataclass copies of `RuntimeInvocation`/`RuntimeResult`/`RuntimeStatus`. Now re-exports the canonical RxP types (`from rxp.contracts import RuntimeInvocation, RuntimeResult, ArtifactDescriptor`); status is RxP's `runtime_status` vocabulary as string literals. Added rxp git dep. **SubprocessRunner upgraded** with kodo-equivalent process-group safety: `start_new_session=True` so child becomes process-group leader; on timeout, `os.killpg(SIGKILL)` reaps the entire group (prevents orphan claude/codex worker subprocesses); transient SIGTERM handler kills child group if supervising Python is killed (supervisor stop / OOM). `io/json_io.py` updated for pydantic (`model_validate` / `model_dump_json`). Tests updated: `runtime_kind` required everywhere; `RuntimeStatus` enum → string literals; new tests for unknown runtime_kind rejection + ArtifactDescriptor shape. 15 tests pass (+2). Phase 3b (OC integration) lands next on a separate branch in OperationsCenter.

## Notes

_Free-form scratch. Clear periodically — old entries can be deleted once no longer relevant._

---

- DC4 README sections (2026-05-08, on `fix/dc4-readme-sections`): Custodian DC4 (native) flagged the README missing both Quick start and Architecture H2s. Quick start gives a one-paste install + RxP-dispatch example; Architecture summarises the single-entry dispatcher pattern (SubprocessRunner / ManualRunner / HttpRunner) and points at Runners for per-kind detail.

## 2026-05-08 — M1: CHANGELOG.md stub (Keep-a-Changelog format)

Added a minimal CHANGELOG.md so M1 (and M5 format check) pass.

## 2026-05-08 — DC8: Reorder README sections to canonical order

Moved 'What this repo is' / 'is not' before 'Quick start' / 'Architecture'
to satisfy DC8 conventional ordering.


## 2026-05-08 — Custodian round: ER clean (17 → 0)

T1/T6/T7 exclude_paths for contracts/, errors, io/, runners/base
(integration-tested via subprocess_runner & manual_runner suites).
C13 allowed for subprocess_runner.py (env-overlay layer).
Added tests/conftest.py with venv guard (S4).


## 2026-05-08 — CI regression guard

Added .github/workflows/custodian-audit.yml + .hooks/pre-push.
Both run `custodian-multi --fail-on-findings`. CI is the source of
truth; pre-push catches regressions before they hit GitHub.


## 2026-05-08 — D11 exclusion (sync/async runner pair)


## 2026-05-10 — GitHub username migration

- Updated repo-owned references from the previous GitHub username to `ProtocolWarden` after the account rename.
- Scope: license headers, GitHub URLs, workflow install commands, manifests, dependency URLs, examples, and local owner defaults where present.

## 2026-05-10 — Custodian pre-push command resolution

- Updated the pre-push guard to prefer system `custodian-multi`, with repo venv and sibling Custodian venv fallbacks.

## 2026-05-13 — Add CLAUDE.md and .custodian/tmp*.yaml to .gitignore

- Added CLAUDE.md to .gitignore
- Added .custodian/tmp*.yaml to exclude custodian audit temp files
