---
id: T-016-github-transport
title: Provide a read-only rate-limited GitHub transport
status: todo
priority: high
spec_ref: specs/v0.1.0.md#read-only-github-ingestion
dependencies:
    - T-015-offline-demo
updated_at: "2026-09-09T19:03:11Z"
---

# T-016-github-transport Provide a read-only rate-limited GitHub transport

## Description

Provide the read-only GitHub transport: an explicit configurable API version
recorded in every extraction manifest, required headers, pagination by link,
conditional requests where applicable, bounded retries with jitter, and respect
for rate limit and `Retry-After` headers. Authentication and permission failures
are distinguished from retryable ones. Redirects and pagination targets are
restricted to the approved API origin.

## Acceptance

- The adapter exposes no method that creates a review, merges, changes labels, assigns a reviewer, or administers a repository.
- A redirect or pagination link to another origin is refused, so credentials are never forwarded.
- A rate-limit response is retried per the documented headers; a permission failure is not retried.
- Tokens are read from the environment and are redacted in every diagnostic, error, and log line.
- Configurable request, page, payload, and record limits are enforced.

## Verification Notes

- Fixture-backed tests including pagination, rate-limit retry, and permission denial.
- A test asserting no token substring appears in any captured log or exception text.

## Implementation Notes
