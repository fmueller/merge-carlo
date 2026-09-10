"""Qualified whole-run bypass accounting; rendering never reruns simulation."""

from dataclasses import asdict, dataclass

from merge_carlo.simulation.domain import PullRequestState
from merge_carlo.simulation.engine import FIFOResult


@dataclass(frozen=True, slots=True)
class BypassSummary:
    eligible_count: int
    audited_count: int
    merges_without_human_review: int
    unreviewed_merge_share: float | None
    unreviewed_merge_share_reason: str | None
    modeled_review_effort_avoided_seconds: float
    defect_escape_rate: None = None
    defect_escape_rate_reason: str = "unsupported_in_v0_1"
    security_risk_change: None = None
    security_risk_change_reason: str = "unsupported_in_v0_1"
    policy_safety: None = None
    policy_safety_reason: str = "unsupported_in_v0_1"


def summarize_bypass(result: FIFOResult) -> BypassSummary:
    """Count admitted work; avoided effort is one assumed visit per bypass.

    This is demand removed at the bypass transition, including proposals later
    abandoned or censored in coordination. It is not a paired baseline saving,
    nor a prediction of further review visits that might have requested changes.
    Measurement-window and mature-cohort metrics belong to the metric layer.
    """
    if result.engine_truncated:
        raise ValueError("cannot summarize an engine_truncated replication")
    merged = [p for p in result.pull_requests if p.state is PullRequestState.MERGED]
    unreviewed = sum(p.review_bypassed and p.review_visit_count == 0 for p in merged)
    return BypassSummary(
        sum(p.bypass_eligible for p in result.pull_requests),
        sum(p.bypass_eligible and p.bypass_audited for p in result.pull_requests),
        unreviewed,
        unreviewed / len(merged) if merged else None,
        None if merged else "no_merges",
        result.modeled_review_effort_avoided_seconds,
    )


def render_bypass_report(summary: BypassSummary) -> str:
    """Render a deterministic qualification and aggregate metrics only."""
    rows = "\n".join(f"- {name}: {'null' if value is None else value}" for name, value in asdict(summary).items())
    return (
        "Hypothetical review bypass (assumed eligibility, audit and effort).\n"
        "The model does not establish policy safety or estimate escaped defects.\n"
        "Removing review also removes modeled review-requested changes; flow gain is "
        "not an estimate of net engineering benefit. No real GitHub action is taken.\n"
        "Avoided effort is one assumed review visit per bypass, not a paired baseline saving; "
        "counts cover admitted work over the whole run.\n" + rows + "\n"
    )
