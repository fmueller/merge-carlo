---
id: T-017-projected-store
title: Persist projected observations in a migrated SQLite store
status: todo
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-016-github-transport
updated_at: "2026-09-09T19:03:11Z"
---

# T-017-projected-store Persist projected observations in a migrated SQLite store

## Description

Persist projected observations in SQLite with explicit migrations and
foreign-key checks: extractions, pull requests, reviews, lifecycle events,
optional CI observations, derived features, collection status, and schema
migrations. Drop bodies, descriptions, diffs, patches, commit messages, email
addresses, avatars, and check output before storage. Content hashes cover sorted
normalized records and canonical JSON.

## Acceptance

- Migrations apply from empty and are recorded; foreign keys are enforced.
- No full raw API payload is persisted by default.
- The same semantic content hashes identically regardless of page layout or extraction completion order.
- Actor identifiers in analytical exports are workspace-scoped HMAC pseudonyms whose mapping and secret stay outside shareable artifacts, with restrictive local permissions.
- All SQL is parameterized.

## Verification Notes

- Privacy tests asserting bodies, patches, emails, and tokens never appear in stored projections.
- A hash-stability test over two differently ordered extractions of the same content.

## Implementation Notes
