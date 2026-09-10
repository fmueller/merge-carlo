"""Leakage-checked empirical features at one frozen training cutoff."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from merge_carlo.simulation.arrivals import TemplateArrival, WeekTemplate
from merge_carlo.simulation.domain import WorkOrigin

Decision = Literal["approved", "changes_requested"]


@dataclass(frozen=True, slots=True)
class SizeSnapshot:
    """Descriptive snapshot known by the cutoff, never a historical size."""

    observed_at: datetime
    additions: int | None
    deletions: int | None
    changed_files: int | None


@dataclass(frozen=True, slots=True)
class PullRequestFeatures:
    pr_id: int
    ready_at: datetime
    author_id: str
    origin: WorkOrigin
    first_substantive_review_elapsed: timedelta | None
    first_observed_decision: Decision | None
    comment_only_reviews: int
    ready_to_merge_elapsed_completion_conditioned: timedelta | None
    fixed_horizon_eligible: bool
    reviewed_within_horizon: bool | None
    merged_within_horizon: bool | None
    size_snapshot: SizeSnapshot | None


@dataclass(frozen=True, slots=True)
class RequestedChangePrevalence:
    """First-decision prevalence among mature PRs decided within the horizon."""

    numerator: int
    denominator: int
    observation_horizon: timedelta
    label: Literal["requested_change_prevalence"] = "requested_change_prevalence"


@dataclass(frozen=True, slots=True)
class ReadyToMerge:
    """Observed merge durations; censored work is intentionally not represented."""

    observations: tuple[timedelta, ...]
    label: Literal["completion_conditioned_ready_to_merge_elapsed"] = "completion_conditioned_ready_to_merge_elapsed"


@dataclass(frozen=True, slots=True)
class CIObservation:
    pr_id: int
    observation_id: int
    conclusion: str | None
    completed_at: datetime
    runtime: timedelta | None


@dataclass(frozen=True, slots=True)
class FeatureSet:
    training_cutoff: datetime
    timezone: str
    outcome_horizon: timedelta
    week_templates: tuple[WeekTemplate, ...]
    pull_requests: tuple[PullRequestFeatures, ...]
    requested_change_prevalence: RequestedChangePrevalence
    ready_to_merge: ReadyToMerge
    ci_observations: tuple[CIObservation, ...]
    ci_coverage: tuple[int, int]


def _rows(data: dict[str, object], name: str) -> list[dict[str, object]]:
    rows = data.get(name)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("invalid projected feature input")
    return cast(list[dict[str, object]], rows)


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid projected feature input")
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid projected feature input") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("invalid projected feature input")
    return result.astimezone(UTC)


def _optional_timestamp(value: object) -> datetime | None:
    return None if value is None else _timestamp(value)


def _actor(row: dict[str, object]) -> str | None:
    user = row.get("user")
    if not isinstance(user, dict):
        return None
    identifier = user.get("id")
    return identifier if isinstance(identifier, str) and identifier else None


def _status(data: dict[str, object], kind: str, pr_id: int | None) -> str | None:
    for row in _rows(data, "collection_status"):
        if row.get("kind") == kind and row.get("pr_id") == pr_id:
            value = row.get("status")
            return value if isinstance(value, str) else None
    return None


def _known_snapshot(row: dict[str, object], cutoff: datetime) -> bool:
    observed_at = _optional_timestamp(row.get("observed_at"))
    return observed_at is not None and observed_at <= cutoff


def _readiness(
    pull: dict[str, object],
    events: list[dict[str, object]],
    feature: dict[str, object],
    cutoff: datetime,
    lifecycle_complete: bool,
) -> datetime | None:
    if not lifecycle_complete:
        return None
    ready_events = sorted(
        _timestamp(row["created_at"])
        for row in events
        if row.get("event") == "ready_for_review" and _timestamp(row["created_at"]) <= cutoff
    )
    event_names = [row.get("event") for row in events]
    if "reopened" in event_names or len(ready_events) > 1 or (ready_events and "converted_to_draft" in event_names):
        return None
    if ready_events:
        return ready_events[0]
    if not _known_snapshot(pull, cutoff):
        return None
    created_at = _timestamp(pull["created_at"])
    if pull.get("draft") is False and _timestamp(pull["updated_at"]) == created_at:
        return created_at
    if feature.get("readiness_policy") == "created_at_proxy":
        return created_at
    return None


def _complete_week_starts(
    analysis_start: datetime, analysis_end: datetime, cutoff: datetime, zone: ZoneInfo
) -> tuple[date, ...]:
    start_local = analysis_start.astimezone(zone)
    first = start_local.date() - timedelta(days=start_local.weekday())
    if start_local != datetime.combine(first, time(), zone):
        first += timedelta(days=7)
    limit = min(analysis_end, cutoff)
    weeks: list[date] = []
    current = first
    while datetime.combine(current + timedelta(days=7), time(), zone).astimezone(UTC) <= limit:
        weeks.append(current)
        current += timedelta(days=7)
    return tuple(weeks)


def _size(pull: dict[str, object], cutoff: datetime) -> SizeSnapshot | None:
    if not _known_snapshot(pull, cutoff):
        return None
    observed_at = _timestamp(pull["observed_at"])
    return SizeSnapshot(
        observed_at,
        cast(int | None, pull.get("additions")),
        cast(int | None, pull.get("deletions")),
        cast(int | None, pull.get("changed_files")),
    )


def build_features(
    data: dict[str, object],
    *,
    cutoff: datetime,
    timezone: str,
    outcome_horizon: timedelta,
    declared_human_reviewers: frozenset[str],
) -> FeatureSet:
    """Build immutable descriptive features using only evidence known by cutoff.

    Reviewers are substantive only when explicitly declared human and different
    from the PR author. Requested changes are prevalence, never a defect label.
    CI coverage is `(validly_attributed, observed)` and runtimes require starts.
    """
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("cutoff must be timezone aware")
    cutoff = cutoff.astimezone(UTC)
    if outcome_horizon <= timedelta(0):
        raise ValueError("outcome horizon must be positive")
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise ValueError("invalid timezone") from None
    manifest = data.get("manifest")
    if data.get("schema_version") != 1 or not isinstance(manifest, dict):
        raise ValueError("invalid projected feature input")
    analysis_start = _timestamp(manifest.get("analysis_start"))
    analysis_end = _timestamp(manifest.get("analysis_end"))
    if analysis_start >= analysis_end:
        raise ValueError("invalid projected feature input")
    if _status(data, "pull_requests", None) != "complete":
        raise ValueError("complete pull-request collection required")

    pulls = {cast(int, row["id"]): row for row in _rows(data, "pull_requests")}
    features = {cast(int, row["pr_id"]): row for row in _rows(data, "derived_features")}
    events_by_pr: dict[int, list[dict[str, object]]] = {}
    for row in _rows(data, "lifecycle_events"):
        created_at = _timestamp(row.get("created_at"))
        if created_at <= cutoff:
            events_by_pr.setdefault(cast(int, row["pr_id"]), []).append(row)
    reviews_by_pr: dict[int, list[dict[str, object]]] = {}
    review_observed_through: dict[int, datetime] = {}
    for row in _rows(data, "reviews"):
        observed_at = _optional_timestamp(row.get("observed_at"))
        if observed_at is not None and observed_at <= cutoff:
            pr_id = cast(int, row["pr_id"])
            review_observed_through[pr_id] = max(review_observed_through.get(pr_id, observed_at), observed_at)
        submitted_at = _optional_timestamp(row.get("submitted_at"))
        if submitted_at is not None and submitted_at <= cutoff and _known_snapshot(row, cutoff):
            reviews_by_pr.setdefault(cast(int, row["pr_id"]), []).append(row)

    built: list[PullRequestFeatures] = []
    for pr_id, pull in sorted(pulls.items()):
        feature = features.get(pr_id)
        if feature is None or not _known_snapshot(pull, cutoff):
            continue
        ready_at = _readiness(
            pull,
            events_by_pr.get(pr_id, []),
            feature,
            cutoff,
            _status(data, "lifecycle_events", pr_id) == "complete",
        )
        author = _actor(pull)
        if ready_at is None or ready_at > cutoff or author is None:
            continue
        reviews_complete = _status(data, "reviews", pr_id) == "complete"
        reviews = sorted(
            reviews_by_pr.get(pr_id, []) if reviews_complete else [],
            key=lambda row: (_timestamp(row["submitted_at"]), row["id"]),
        )
        human_reviews = [
            row
            for row in reviews
            if _actor(row) in declared_human_reviewers
            and _actor(row) != author
            and _timestamp(row["submitted_at"]) >= ready_at
        ]
        comments = sum(row.get("state") == "COMMENTED" for row in human_reviews)
        substantive = [row for row in human_reviews if row.get("state") in ("APPROVED", "CHANGES_REQUESTED")]
        first_review = substantive[0] if substantive else None
        first_at = _timestamp(first_review["submitted_at"]) if first_review else None
        decision: Decision | None = None
        if first_review is not None:
            decision = "approved" if first_review["state"] == "APPROVED" else "changes_requested"
        merged_at = _optional_timestamp(pull.get("merged_at"))
        if merged_at is not None and not ready_at <= merged_at <= cutoff:
            merged_at = None
        horizon_end = ready_at + outcome_horizon
        mature = (
            horizon_end <= cutoff
            and reviews_complete
            and _timestamp(pull["observed_at"]) >= horizon_end
            and review_observed_through.get(pr_id, datetime.min.replace(tzinfo=UTC)) >= horizon_end
        )
        reviewed_within_horizon = None
        merged_within_horizon = None
        if mature:
            reviewed_within_horizon = first_at is not None and first_at <= ready_at + outcome_horizon
            merged_within_horizon = merged_at is not None and merged_at <= ready_at + outcome_horizon
        built.append(
            PullRequestFeatures(
                pr_id=pr_id,
                ready_at=ready_at,
                author_id=author,
                origin=WorkOrigin(cast(str, feature.get("origin"))),
                first_substantive_review_elapsed=first_at - ready_at if first_at else None,
                first_observed_decision=decision,
                comment_only_reviews=comments,
                ready_to_merge_elapsed_completion_conditioned=merged_at - ready_at if merged_at else None,
                fixed_horizon_eligible=mature,
                reviewed_within_horizon=reviewed_within_horizon,
                merged_within_horizon=merged_within_horizon,
                size_snapshot=_size(pull, cutoff),
            )
        )

    week_starts = _complete_week_starts(analysis_start, analysis_end, cutoff, zone)
    arrivals: dict[date, list[TemplateArrival]] = {week: [] for week in week_starts}
    for built_row in built:
        local = built_row.ready_at.astimezone(zone)
        week = local.date() - timedelta(days=local.weekday())
        if week in arrivals:
            offset = local.replace(tzinfo=None) - datetime.combine(week, time())
            arrivals[week].append(TemplateArrival(offset, built_row.author_id, built_row.origin))
    templates = tuple(
        WeekTemplate(week, tuple(sorted(rows, key=lambda row: (row.offset, row.author_id))))
        for week, rows in arrivals.items()
    )

    prevalence_rows = [
        row
        for row in built
        if row.fixed_horizon_eligible
        and row.first_substantive_review_elapsed is not None
        and row.first_substantive_review_elapsed <= outcome_horizon
    ]
    prevalence = RequestedChangePrevalence(
        sum(row.first_observed_decision == "changes_requested" for row in prevalence_rows),
        len(prevalence_rows),
        outcome_horizon,
    )
    merge_durations = tuple(
        row.ready_to_merge_elapsed_completion_conditioned
        for row in built
        if row.ready_to_merge_elapsed_completion_conditioned is not None
    )

    ci_candidates = [
        row
        for row in _rows(data, "ci_observations")
        if (completed_at := _optional_timestamp(row.get("completed_at"))) is not None
        and completed_at <= cutoff
        and _status(data, "ci_observations", cast(int, row.get("pr_id"))) == "complete"
    ]
    ci: list[CIObservation] = []
    for ci_row in ci_candidates:
        pr_id = cast(int, ci_row["pr_id"])
        ci_pull = pulls.get(pr_id)
        head = ci_pull.get("head") if ci_pull and _known_snapshot(ci_pull, cutoff) else None
        if not isinstance(head, dict) or ci_row.get("head_sha") != head.get("sha"):
            continue
        completed_at = _timestamp(ci_row["completed_at"])
        started_at = _optional_timestamp(ci_row.get("started_at"))
        runtime = completed_at - started_at if started_at is not None and started_at <= completed_at else None
        ci.append(
            CIObservation(
                pr_id,
                cast(int, ci_row["id"]),
                cast(str | None, ci_row.get("conclusion")),
                completed_at,
                runtime,
            )
        )

    return FeatureSet(
        training_cutoff=cutoff,
        timezone=timezone,
        outcome_horizon=outcome_horizon,
        week_templates=templates,
        pull_requests=tuple(built),
        requested_change_prevalence=prevalence,
        ready_to_merge=ReadyToMerge(merge_durations),
        ci_observations=tuple(sorted(ci, key=lambda row: (row.pr_id, row.completed_at, row.observation_id))),
        ci_coverage=(len(ci), len(ci_candidates)),
    )
