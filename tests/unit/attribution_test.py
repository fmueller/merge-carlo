"""Readiness and work-origin resolution from projected GitHub observations."""

from datetime import datetime
from pathlib import Path

import pytest

from merge_carlo.attribution import AttributionConfig, OriginDeclaration, resolve_attribution

pytestmark = pytest.mark.unit


def pull(**fields: object) -> dict[str, object]:
    return {
        "id": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-03T00:00:00Z",
        "draft": False,
        "user": {"id": 42, "type": "User"},
        **fields,
    }


def event(identifier: int, name: str, at: str) -> dict[str, object]:
    return {"id": identifier, "event": name, "created_at": at}


def test_strict_readiness_uses_observed_event_not_latest_non_draft_snapshot() -> None:
    observed = resolve_attribution(
        pull(),
        [event(2, "ready_for_review", "2026-01-02T00:00:00Z")],
        AttributionConfig(),
    )
    unknown = resolve_attribution(pull(), [], AttributionConfig())

    assert (observed["ready_at"], observed["readiness_basis"]) == (
        "2026-01-02T00:00:00Z",
        "observed_event",
    )
    assert (unknown["ready_at"], unknown["readiness_basis"]) == (None, "unknown")
    assert unknown["readiness_policy"] == "strict"
    assert (unknown["fit_eligible"], unknown["fit_exclusion_reason"]) == (False, "unknown_readiness")


def test_supported_reconstruction_requires_creation_snapshot_evidence() -> None:
    result = resolve_attribution(
        pull(updated_at="2026-01-01T00:00:00Z"),
        [],
        AttributionConfig(),
    )

    assert (result["ready_at"], result["readiness_basis"]) == (
        "2026-01-01T00:00:00Z",
        "supported_reconstruction",
    )


def test_created_at_proxy_is_explicit_and_recorded() -> None:
    result = resolve_attribution(pull(draft=None), [], AttributionConfig(readiness_policy="created_at_proxy"))

    assert (result["ready_at"], result["readiness_basis"], result["readiness_policy"]) == (
        "2026-01-01T00:00:00Z",
        "created_at_proxy",
        "created_at_proxy",
    )


@pytest.mark.parametrize(
    ("events", "reason"),
    [
        ([event(2, "reopened", "2026-01-04T00:00:00Z")], "reopened"),
        (
            [
                event(2, "ready_for_review", "2026-01-02T00:00:00Z"),
                event(3, "converted_to_draft", "2026-01-03T00:00:00Z"),
                event(4, "ready_for_review", "2026-01-04T00:00:00Z"),
            ],
            "repeated_readiness_cycle",
        ),
    ],
)
def test_ambiguous_lifecycles_remain_in_output_but_are_excluded_from_fit(
    events: list[dict[str, object]], reason: str
) -> None:
    result = resolve_attribution(pull(), events, AttributionConfig())

    assert result["id"] == 1
    assert (result["fit_eligible"], result["fit_exclusion_reason"]) == (False, reason)


def test_actor_kind_does_not_determine_work_origin_and_null_author_stays_unknown() -> None:
    bot = resolve_attribution(pull(user={"id": 42, "type": "Bot"}), [], AttributionConfig())
    missing = resolve_attribution(pull(user=None), [], AttributionConfig())

    assert (bot["origin"], bot["origin_basis"]) == ("unknown", "unmapped")
    assert (missing["origin"], missing["origin_basis"]) == ("unknown", "missing_author")


def test_mapping_conflicts_use_strongest_basis_and_ties_stay_unknown() -> None:
    strongest = AttributionConfig(
        actor_origins=(
            OriginDeclaration(actor_id=42, origin="human", basis="assumed"),
            OriginDeclaration(actor_id=42, origin="ai", basis="observed"),
        )
    )
    tied = AttributionConfig(
        actor_origins=(
            OriginDeclaration(actor_id=42, origin="human", basis="assumed"),
            OriginDeclaration(actor_id=42, origin="ai", basis="assumed"),
        )
    )

    assert (
        resolve_attribution(pull(), [], strongest)["origin"],
        resolve_attribution(pull(), [], strongest)["origin_basis"],
    ) == (
        "ai",
        "observed",
    )
    assert (resolve_attribution(pull(), [], tied)["origin"], resolve_attribution(pull(), [], tied)["origin_basis"]) == (
        "unknown",
        "conflicting_mapping",
    )


def test_config_loads_safe_bounded_yaml_and_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "origins.yaml"
    path.write_text(
        "readiness_policy: strict\nactor_origins:\n  - actor_id: 42\n    origin: ai\n    basis: assumed\n",
        encoding="utf-8",
    )

    config = AttributionConfig.from_yaml(path)

    assert config.actor_origins == (OriginDeclaration(actor_id=42, origin="ai", basis="assumed"),)
    path.write_text("readiness_policy: strict\nai_generated_ratio: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid attribution config"):
        AttributionConfig.from_yaml(path)


def test_oversized_config_is_rejected_without_unbounded_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "origins.yaml"
    path.write_bytes(b" " * 1_000_001)
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("unbounded config read"))

    with pytest.raises(ValueError, match="invalid attribution config"):
        AttributionConfig.from_yaml(path)


def test_resolution_does_not_mutate_inputs() -> None:
    source_pull = pull()
    source_events = [event(2, "ready_for_review", "2026-01-02T00:00:00Z")]
    before = (source_pull.copy(), [item.copy() for item in source_events])

    resolve_attribution(source_pull, source_events, AttributionConfig())

    assert (source_pull, source_events) == before
    assert isinstance(datetime.fromisoformat(str(source_pull["created_at"])), datetime)
