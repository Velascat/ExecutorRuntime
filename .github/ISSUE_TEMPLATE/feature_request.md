---
name: Feature Request
about: Suggest an improvement or new capability
labels: enhancement
assignees: ''
---

## Summary

A one-sentence description of the feature.

## Problem It Solves

What is currently difficult or impossible that this would fix?

## Proposed Solution

How you imagine it working. Include API examples if relevant.

## Affected Layer

Which part of ExecutorRuntime does this touch?

- [ ] RuntimeInvocation contract (input parsing/validation)
- [ ] Runner protocol / abstract base
- [ ] SubprocessRunner implementation
- [ ] New runner (specify kind):
- [ ] cwd / environment handling
- [ ] Timeout mechanism
- [ ] Capture / artifact collection
- [ ] RuntimeResult contract (output serialization)
- [ ] Tests / fixtures

## Alternatives Considered

Other approaches and why you ruled them out.

## Scope Check

Confirm this change stays within ExecutorRuntime's scope:
- It belongs to runtime execution mechanics (not scheduling, routing, planning)
- It does not duplicate functionality from SourceRegistry, SwitchBoard, OperationsCenter, or RxP
- The input/output contracts remain RxP-compatible

## Additional Context

Related issues, architecture docs, or prior discussion.
