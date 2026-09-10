# Frozen-cutoff feature builder

`merge_carlo.features.build_features` converts a projected-store export into
immutable empirical features for model calibration. It requires a timezone-aware
training cutoff, the source dataset's canonical content hash and readiness
policy, a positive fixed outcome horizon, one declared timezone, and a set of
pseudonymous actor IDs explicitly declared to be human reviewers. The source
hash travels with the feature set so calibration cannot associate its features
with another dataset's coverage.

The builder fails closed unless pull-request enumeration is complete. It only
certifies Monday-based local calendar weeks wholly inside the requested analysis
interval and at or before the cutoff, retaining empty weeks and each arrival's
wall-clock offset, author, and declared work origin. Readiness is reconstructed
from cutoff-bounded lifecycle events or a snapshot observed by the cutoff;
incomplete or repeated lifecycle histories do not enter arrival templates.

A substantive review is the first submitted approval or changes-requested review
after readiness by a declared-human non-author. Pending drafts are not
submissions, and human comment-only submissions have a separate count. An
incomplete review collection cannot establish a first review or fixed-horizon
outcome. Requested-change prevalence is explicitly labeled, carries its mature
within-horizon decision denominator, and is not a defect rate.

Merge durations are emitted only for merges observed by the cutoff and are
named `completion_conditioned_ready_to_merge_elapsed`; they are not an
uncensored population distribution. Fixed-horizon reviewed and merged outcomes
are defined only for mature rows whose review observations and PR snapshot cover
the horizon endpoint and are known by the cutoff. Empty review collections lack
an observation timestamp in v0.1.0, so they cannot certify a negative outcome.
Size fields retain their observation time and are descriptive metadata only;
snapshots first observed later are omitted entirely, including their author and
derived origin attribution.

Optional CI observations are counted only when completed by the cutoff. A
feature is emitted only when its SHA matches the PR head snapshot known by the
cutoff, and runtime is absent when no valid start time exists. `ci_coverage` is
the `(validly_attributed, observed)` count. CI collection remains optional and
is implemented separately from this feature boundary.
