---
id: T-048-prepare-end-to-end-held-out-validation
title: Prepare end-to-end held-out validation from collected datasets
status: todo
priority: high
spec_ref: specs/v0.2.0.md#end-to-end-holdout-validation-preparation
dependencies:
    - T-024-held-out-validation
updated_at: "2026-09-17T21:06:45Z"
---

# T-048-prepare-end-to-end-held-out-validation Prepare end-to-end held-out validation from collected datasets

## Description

Complete the real-data path from a collected projected dataset to a
chronological holdout validation run. The preparation workflow freezes the
training cutoff, builds features and calibrates only from the fitting interval,
derives known-at-arrival replay inputs, and emits the versioned evidence
consumed by `merge-carlo validate`. Keep the in-sample diagnostic escape hatch
explicit and preserve content-hash lineage.

## Acceptance

- A collected dataset can be split at an explicit UTC training cutoff without
  holdout arrivals or outcomes entering feature construction or calibration.
- The preparation workflow emits a schema-validated replay-evidence artifact
  with non-overlapping fitting and validation intervals, mature-cohort
  follow-up checks, and dataset/model/arrival content hashes.
- A fresh Helm or equivalent public-repository run executes `merge-carlo
  validate --strict` with the emitted evidence and is labeled `held_out`, not
  `in_sample_diagnostic`; a failed declared gate remains a held-out failure,
  not a mislabeled success.
- Unknown readiness and work-origin attribution remain explicit; the workflow
  does not infer active effort from elapsed review delay.
- Documentation includes the workflow, split semantics, and the distinction
  between descriptive holdout validation and intervention validity.

## Verification Notes

- Unit tests cover temporal leakage, insufficient seven-day follow-up, malformed
  evidence, and content-hash lineage.
- An integration test exercises collected fixture data through evidence
  preparation and strict validation.

## Implementation Notes
