---
id: T-026-schema-export
title: Export the configuration JSON Schemas from the CLI
status: todo
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies:
    - T-023-model-builder
updated_at: "2026-09-09T19:03:12Z"
---

# T-026-schema-export Export the configuration JSON Schemas from the CLI

## Description

Export the configuration JSON Schemas from the CLI and finish the configuration
contract: strict validation, rejection of unknown keys, safe YAML loading, and
documented multiplier composition for effort sensitivity.

## Acceptance

- A command writes the assumption and scenario JSON Schemas to a chosen path.
- Unknown configuration keys are rejected rather than ignored.
- YAML loading constructs no arbitrary Python object, and no configuration value can execute code or a shell command.
- Sampled active service rounds up to whole seconds with a one-second minimum; a constant zero delay is allowed only for permitted coordination phases and test fixtures.
- The effort multiplier composition is documented in the schema.

## Verification Notes

- A test loading a YAML document containing a Python object tag and asserting it is refused.
- Round-trip tests validating the shipped example configurations against the exported schemas.

## Implementation Notes
