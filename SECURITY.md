# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes     |

Only the current `main` branch receives security fixes.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately by emailing **coding.projects.1642@proton.me**.

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations (optional)

You will receive an acknowledgment within 72 hours. We aim to release a fix within 14 days of a confirmed report, depending on severity and complexity.

## Scope

ExecutorRuntime executes subprocess commands derived from RxP `RuntimeInvocation` inputs. The primary security surface is:

- **Arbitrary command execution** via the `command` field of an invocation — callers are responsible for vetting inputs; ExecutorRuntime executes what it is told
- **Working directory escape** via `cwd` traversal patterns
- **Environment variable injection** via the `env_overlay` field — secrets in the parent environment may be inherited if not explicitly cleared
- **Argument injection** when callers concatenate untrusted strings into `command`
- **Timeout bypass** — the timeout mechanism must not be circumventable by the spawned subprocess
- **Artifact path traversal** — `artifact_globs` must not be exploitable to read files outside the working directory

## Out of Scope

- Vulnerabilities in the binaries that ExecutorRuntime invokes (e.g. `git`, `bun`, `python`); those are upstream concerns
- Caller-side input validation — sanitizing untrusted input before constructing a `RuntimeInvocation` is the caller's responsibility
- Issues requiring physical access to the host machine
- Resource exhaustion via legitimate but heavy workloads (timeouts and resource limits are configuration concerns)
