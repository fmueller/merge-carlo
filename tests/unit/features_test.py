"""Frozen-cutoff empirical feature extraction from projected observations."""

from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from merge_carlo.features import FeatureSet, build_features
from merge_carlo.simulation.domain import WorkOrigin

pytestmark = pytest.mark.unit
CUTOFF = datetime.fromisoformat("2026-01-15T00:00:00Z")
HORIZON = timedelta(days=2)


def fixture() -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest": {
            "repository_id": 17,
            "api_version": "2022-11-28",
            "analysis_start": "2026-01-05T00:00:00Z",
            "analysis_end": "2026-01-19T00:00:00Z",
        },
        "pull_requests": [
            {
                "id": 1,
                "number": 11,
                "state": "closed",
                "created_at": "2026-01-04T00:00:00Z",
                "updated_at": "2026-01-08T00:00:00Z",
                "observed_at": "2026-01-10T00:00:00Z",
                "merged_at": "2026-01-08T12:00:00Z",
                "user": {"id": "author-1", "type": "User"},
                "head": {"sha": "a" * 40},
                "additions": 8,
                "deletions": 3,
                "changed_files": 2,
            },
            {
                "id": 2,
                "number": 12,
                "state": "open",
                "created_at": "2026-01-12T09:00:00Z",
                "updated_at": "2026-01-12T09:00:00Z",
                "observed_at": "2026-01-14T12:00:00Z",
                "merged_at": None,
                "draft": False,
                "user": {"id": "author-2", "type": "User"},
                "head": {"sha": "b" * 40},
                "additions": 5,
                "deletions": 1,
                "changed_files": 1,
            },
        ],
        "derived_features": [
            {
                "id": 1,
                "pr_id": 1,
                "ready_at": "2026-01-05T09:00:00Z",
                "readiness_basis": "observed_event",
                "readiness_policy": "strict",
                "origin": "human",
                "origin_basis": "assumed",
                "fit_eligible": True,
                "fit_exclusion_reason": None,
                "basis": "derived",
            },
            {
                "id": 2,
                "pr_id": 2,
                "ready_at": "2026-01-12T09:00:00Z",
                "readiness_basis": "supported_reconstruction",
                "readiness_policy": "strict",
                "origin": "ai",
                "origin_basis": "assumed",
                "fit_eligible": True,
                "fit_exclusion_reason": None,
                "basis": "derived",
            },
        ],
        "reviews": [
            {
                "id": 10,
                "pr_id": 1,
                "state": "PENDING",
                "submitted_at": None,
                "observed_at": "2026-01-10T00:00:00Z",
                "user": {"id": "human-1", "type": "User"},
            },
            {
                "id": 11,
                "pr_id": 1,
                "state": "COMMENTED",
                "submitted_at": "2026-01-05T10:00:00Z",
                "observed_at": "2026-01-10T00:00:00Z",
                "user": {"id": "human-1", "type": "User"},
            },
            {
                "id": 12,
                "pr_id": 1,
                "state": "APPROVED",
                "submitted_at": "2026-01-05T11:00:00Z",
                "observed_at": "2026-01-10T00:00:00Z",
                "user": {"id": "author-1", "type": "User"},
            },
            {
                "id": 13,
                "pr_id": 1,
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2026-01-05T13:00:00Z",
                "observed_at": "2026-01-10T00:00:00Z",
                "user": {"id": "human-1", "type": "User"},
            },
            {
                "id": 20,
                "pr_id": 2,
                "state": "APPROVED",
                "submitted_at": "2026-01-14T12:00:00Z",
                "observed_at": "2026-01-14T13:00:00Z",
                "user": {"id": "human-1", "type": "User"},
            },
        ],
        "lifecycle_events": [
            {
                "id": 40,
                "pr_id": 1,
                "event": "ready_for_review",
                "created_at": "2026-01-05T09:00:00Z",
            }
        ],
        "ci_observations": [
            {
                "id": 30,
                "pr_id": 1,
                "status": "completed",
                "conclusion": "failure",
                "started_at": "2026-01-05T09:30:00Z",
                "completed_at": "2026-01-05T09:40:00Z",
                "head_sha": "a" * 40,
            },
            {
                "id": 31,
                "pr_id": 1,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-01-05T09:31:00Z",
                "completed_at": "2026-01-05T09:41:00Z",
                "head_sha": "c" * 40,
            },
        ],
        "collection_status": [
            {"kind": "pull_requests", "pr_id": None, "status": "complete", "reason": None},
            {"kind": "reviews", "pr_id": 1, "status": "complete", "reason": None},
            {"kind": "reviews", "pr_id": 2, "status": "complete", "reason": None},
            {"kind": "lifecycle_events", "pr_id": 1, "status": "complete", "reason": None},
            {"kind": "lifecycle_events", "pr_id": 2, "status": "complete", "reason": None},
            {"kind": "ci_observations", "pr_id": 1, "status": "complete", "reason": None},
            {"kind": "ci_observations", "pr_id": 2, "status": "not_requested", "reason": None},
        ],
    }


def build(data: dict[str, object] | None = None) -> FeatureSet:
    return build_features(
        data or fixture(),
        dataset_content_hash="a" * 64,
        readiness_policy="strict",
        cutoff=CUTOFF,
        timezone="UTC",
        outcome_horizon=HORIZON,
        declared_human_reviewers=frozenset({"human-1"}),
    )


def test_hand_computed_features_and_labels() -> None:
    result = build()

    assert len(result.week_templates) == 1
    week = result.week_templates[0]
    assert week.week_start.isoformat() == "2026-01-05"
    assert [(arrival.offset, arrival.author_id, arrival.origin) for arrival in week.arrivals] == [
        (timedelta(hours=9), "author-1", WorkOrigin.HUMAN)
    ]

    first, second = result.pull_requests
    assert first.first_substantive_review_elapsed == timedelta(hours=4)
    assert first.first_observed_decision == "changes_requested"
    assert first.comment_only_reviews == 1
    assert first.ready_to_merge_elapsed_completion_conditioned == timedelta(days=3, hours=3)
    assert (first.fixed_horizon_eligible, first.reviewed_within_horizon, first.merged_within_horizon) == (
        True,
        True,
        False,
    )
    assert first.size_snapshot is not None
    assert (first.size_snapshot.additions, first.size_snapshot.deletions, first.size_snapshot.changed_files) == (
        8,
        3,
        2,
    )
    assert second.first_substantive_review_elapsed == timedelta(days=2, hours=3)
    assert (second.fixed_horizon_eligible, second.reviewed_within_horizon, second.merged_within_horizon) == (
        True,
        False,
        False,
    )

    prevalence = result.requested_change_prevalence
    assert prevalence.label == "requested_change_prevalence"
    assert (prevalence.numerator, prevalence.denominator, prevalence.observation_horizon) == (1, 1, HORIZON)
    assert result.ready_to_merge.label == "completion_conditioned_ready_to_merge_elapsed"
    assert result.ready_to_merge.observations == (timedelta(days=3, hours=3),)
    assert result.ci_coverage == (1, 2)
    assert len(result.ci_observations) == 1
    assert result.ci_observations[0].runtime == timedelta(minutes=10)


def test_post_cutoff_source_and_snapshot_attributes_cannot_leak() -> None:
    baseline = build()
    data = deepcopy(fixture())
    pulls = data["pull_requests"]
    assert isinstance(pulls, list)
    pulls[0]["merged_at"] = "2026-01-16T00:00:00Z"
    pulls[0]["additions"] = 999_999
    pulls[0]["observed_at"] = "2026-01-16T01:00:00Z"
    reviews = data["reviews"]
    assert isinstance(reviews, list)
    reviews.append(
        {
            "id": 99,
            "pr_id": 2,
            "state": "CHANGES_REQUESTED",
            "submitted_at": "2026-01-15T01:00:00Z",
            "observed_at": "2026-01-15T02:00:00Z",
            "user": {"id": "human-1", "type": "User"},
        }
    )

    changed = build(data)

    assert [row.pr_id for row in changed.pull_requests] == [2]
    assert changed.pull_requests[0] == baseline.pull_requests[1]
    assert changed.week_templates[0].arrivals == ()
    assert (changed.requested_change_prevalence.numerator, changed.requested_change_prevalence.denominator) == (0, 0)


@pytest.mark.parametrize("late_evidence", ["pull", "reviews"])
def test_fixed_horizon_negatives_require_evidence_through_horizon(late_evidence: str) -> None:
    data = fixture()
    pulls = data["pull_requests"]
    reviews = data["reviews"]
    assert isinstance(pulls, list)
    assert isinstance(reviews, list)
    if late_evidence == "pull":
        pulls[1]["observed_at"] = "2026-01-13T00:00:00Z"
    else:
        reviews[-1]["submitted_at"] = "2026-01-13T00:00:00Z"
        reviews[-1]["observed_at"] = "2026-01-16T00:00:00Z"

    second = build(data).pull_requests[1]

    assert (second.fixed_horizon_eligible, second.reviewed_within_horizon, second.merged_within_horizon) == (
        False,
        None,
        None,
    )


def test_incomplete_collections_cannot_certify_empty_weeks_or_first_reviews() -> None:
    data = fixture()
    statuses = data["collection_status"]
    assert isinstance(statuses, list)
    statuses[0]["status"] = "partial"
    with pytest.raises(ValueError, match="complete pull-request collection"):
        build(data)

    data = fixture()
    statuses = data["collection_status"]
    assert isinstance(statuses, list)
    statuses[1]["status"] = "partial"
    result = build(data)
    first = result.pull_requests[0]
    assert first.first_substantive_review_elapsed is None
    assert first.first_observed_decision is None
    assert first.comment_only_reviews == 0
    assert (first.fixed_horizon_eligible, first.reviewed_within_horizon, first.merged_within_horizon) == (
        False,
        None,
        None,
    )
    assert result.requested_change_prevalence.denominator == 0


@pytest.mark.parametrize(
    "cutoff,horizon,timezone,match",
    [
        (datetime(2026, 1, 15), HORIZON, "UTC", "cutoff"),
        (CUTOFF, timedelta(0), "UTC", "horizon"),
        (CUTOFF, HORIZON, "not/a-zone", "timezone"),
    ],
)
def test_invalid_feature_boundary_inputs(cutoff: datetime, horizon: timedelta, timezone: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        build_features(
            fixture(),
            dataset_content_hash="a" * 64,
            readiness_policy="strict",
            cutoff=cutoff,
            timezone=timezone,
            outcome_horizon=horizon,
            declared_human_reviewers=frozenset(),
        )
