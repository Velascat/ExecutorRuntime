---
name: Bug Report
about: Something is broken or behaving unexpectedly
labels: bug
assignees: ''
---

## Description

A clear description of what is broken.

## Steps to Reproduce

1. 
2. 
3. 

## Expected Behavior

What should have happened.

## Actual Behavior

What actually happened. Include the runtime stage where it failed:

- [ ] Invocation parsing / contract validation
- [ ] Subprocess spawn
- [ ] cwd / env overlay
- [ ] Timeout enforcement
- [ ] stdout/stderr capture
- [ ] Exit-code normalization
- [ ] Artifact collection
- [ ] Result serialization

## Runner

Which runner exhibited the bug?

- [ ] SubprocessRunner
- [ ] Other (specify):

## Environment

- OS: 
- Python version: 
- ExecutorRuntime version / commit: 
- Binary being invoked (e.g. git, bun, python):

## Relevant Output

```
paste any error messages, stderr, or RuntimeResult JSON here
```

## RuntimeInvocation (if available)

```json
{ ... paste the invocation JSON that triggered the bug ... }
```

## Additional Context

Anything else that might be relevant.
