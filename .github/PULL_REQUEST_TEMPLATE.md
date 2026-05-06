## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Changes

<!-- Bullet list of what changed. -->

-

## Scope Check

- [ ] Change stays within runtime execution mechanics (subprocess, cwd, env, timeout, capture, artifacts)
- [ ] No scheduling, routing, or planning logic introduced
- [ ] No source/fork management logic introduced (that's SourceRegistry)
- [ ] Public input/output contracts still match RxP shapes

## Testing

- [ ] Tests pass: `pytest -q`
- [ ] Linter passes: `ruff check src/`
- [ ] New behavior is covered by tests
- [ ] Failure paths tested (timeout, non-zero exit, missing binary, etc.)

## Related Issues

<!-- Closes #N or References #N -->

## Notes for Reviewer

<!-- Anything non-obvious: edge cases, runner-specific behavior, follow-ups. -->
