---
id: T-036-reopen-completed-work
title: Support reopening completed tracked work
status: todo
priority: low
spec_ref: specs/v0.2.0.md#tracked-work-tooling
dependencies: []
updated_at: "2026-09-11T10:31:03Z"
---

# T-036-reopen-completed-work Support reopening completed tracked work

## Description

Release applicability: v0.2.0 tracked-work tooling follow-up (moved from v0.1.0
by maintainer decision on 2026-09-11), not a simulator feature or release
correctness blocker. Taskrail 0.4.0 cannot reopen completed
work when the user changes the acceptance decision before commit. During
T-035, `start` rejected completed as not todo; `block` rejected it as not
transitionable; `unblock` requires blocked. No status fields were hand-edited.
Resolve the upstream CLI capability or document a supported lifecycle for this
case without implementing Taskrail internals in merge-carlo.

## Acceptance

- A documented, supported command path handles revised completed work without
  hand-editing machine-managed fields or erasing prior verification history.
- Any toolchain upgrade is pinned and checked with repository setup and gates.

## Verification Notes

- Reproduce on disposable planning data: complete a task, revise its requested
  outcome, reopen, verify, and complete again while retaining history.

## Implementation Notes

Filed only during T-035. Not implemented here. T-035's completed status from
the superseded draft remains until fresh final verification is recorded; its
task notes distinguish the changed acceptance decision from the earlier pass.
