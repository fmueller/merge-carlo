# Model card template

Every calibrated model emits a `model-card.md` built from this template. Fields
that cannot be filled are rendered as `null` with a reason, never omitted and
never defaulted to a favorable value.

## Identity

- Model version, application version, schema version.
- Source dataset content hash, feature version, training cutoff.
- Assumptions content hash, reference timezone.
- Seed and RNG scheme version, Python and dependency versions.
- `synthetic_data` flag.

## Evidence status

One of: synthetic demonstration, `exploratory_only`, or held-out descriptive
pass, with the date and scope of that determination.

## Data coverage

- Repository, requested analysis window, retrieval times.
- Pull request, review, lifecycle, and CI collection status: `complete`,
  `partial`, `unavailable`, or `not_requested`.
- Readiness basis distribution: `observed_event`, `supported_reconstruction`,
  `created_at_proxy`, `unknown`, and the readiness policy in force.
- Origin attribution coverage and the fraction that stayed `unknown`.
- Excluded lifecycle fractions and the reason for each exclusion.
- Complete training weeks available.

## Parameters

For each parameter: value specification, unit, provenance basis (`observed`,
`derived`, `proxy`, `assumed`, `synthetic`), relevant sample count, missingness
treatment, any grouping or fallback rule, and evidence references. A
hand-entered assumption carries no confidence interval unless it is itself a
declared assumption distribution.

## Workflow assumptions

The modeled workflow class, the review scheduling rule, the reviewer roster and
whether it is identity-bound or synthetic capacity slots, and the initialization
scheme.

## Evidence flags

Any triggered safeguard: too few usable pull requests, too few substantive
decisions for a cohort estimate, insufficient complete weeks, or excessive
unknown readiness.

## Limitations

A pointer to `docs/limitations.md` plus any limitation specific to this dataset.
