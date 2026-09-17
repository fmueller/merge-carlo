---
id: T-051-declare-professional-workflow-compatibility-profiles
title: Declare professional workflow compatibility profiles
status: todo
priority: medium
spec_ref: specs/v0.3.0.md#professional-workflow-profiles
dependencies:
    - T-048-prepare-end-to-end-held-out-validation
updated_at: "2026-09-17T21:28:33Z"
---

# T-051-declare-professional-workflow-compatibility-profiles Declare professional workflow compatibility profiles

## Description

Add a versioned, typed workflow-profile contract for repository policies that
the single-reviewer FIFO model cannot safely assume. The profile must make
approval requirements, reviewer routing, merge gating and queues,
closure-without-delivery, initial backlog, and audited-work policy explicit so
Helm-like data is rejected or qualified rather than silently simplified.

## Acceptance

- Profiles record each workflow dimension with provenance and a status of
  `supported`, `partial`, or `unavailable`.
- Validation and reports expose structural-fit limitations when a profile uses
  unsupported approval, routing, queue, closure, audit, or backlog semantics;
  unsupported dimensions are never treated as favorable zeros.
- Supported aggregate approximations and explicit rejection behavior are
  documented without adding hidden CODEOWNERS or branch-protection heuristics.
- Tests cover a fully supported profile, a partially supported profile, and a
  rejected validation profile while preserving deterministic artifact hashes.

## Verification Notes

- Use synthetic fixtures for multiple approvals, routed reviewers, merge queues,
  close-without-merge, and nonzero initial backlog.
- Run schema, workflow-profile, validation, reporting, lint, type, and test
  checks; inspect generated limitations text.

## Implementation Notes
