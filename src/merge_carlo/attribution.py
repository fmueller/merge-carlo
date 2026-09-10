"""Conservative readiness and declared work-origin attribution."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

Origin = Literal["human", "ai", "non_ai_automation", "unknown"]
ProvenanceBasis = Literal["observed", "derived", "proxy", "assumed", "synthetic"]
OriginBasis = ProvenanceBasis | Literal["unmapped", "missing_author", "conflicting_mapping"]
ReadinessBasis = Literal["observed_event", "supported_reconstruction", "created_at_proxy", "unknown"]
ReadinessPolicy = Literal["strict", "created_at_proxy"]
FitExclusion = Literal["reopened", "repeated_readiness_cycle", "incomplete_lifecycle", "unknown_readiness"]

_BASIS_STRENGTH: dict[ProvenanceBasis, int] = {
    "observed": 4,
    "derived": 3,
    "proxy": 2,
    "assumed": 1,
    "synthetic": 0,
}


class OriginDeclaration(BaseModel):
    """One operator-supplied assertion about an immutable GitHub actor ID."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    actor_id: int = Field(strict=True, gt=0, le=2**63 - 1)
    origin: Literal["human", "ai", "non_ai_automation"]
    basis: ProvenanceBasis


class AttributionConfig(BaseModel):
    """Local attribution choices; no actor mapping is inferred from account kind."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    readiness_policy: ReadinessPolicy = "strict"
    actor_origins: tuple[OriginDeclaration, ...] = ()

    @classmethod
    def from_yaml(cls, path: Path) -> "AttributionConfig":
        """Load a small data-only local configuration with static diagnostics."""
        try:
            with path.open("rb") as stream:
                raw = stream.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError
            data = yaml.safe_load(raw.decode("utf-8"))
            if data is None:
                data = {}
            return cls.model_validate(data)
        except (OSError, UnicodeError, yaml.YAMLError, ValidationError, ValueError):
            raise ValueError("invalid attribution config") from None


class Attribution(TypedDict):
    id: int
    ready_at: str | None
    readiness_basis: ReadinessBasis
    readiness_policy: ReadinessPolicy
    origin: Origin
    origin_basis: OriginBasis
    fit_eligible: bool
    fit_exclusion_reason: FitExclusion | None
    basis: Literal["derived"]


def _timestamp(value: object) -> datetime:
    result = datetime.fromisoformat(cast(str, value))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("invalid projected observation")
    return result.astimezone(UTC)


def _render(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _readiness(
    pull: dict[str, object], events: list[dict[str, object]], policy: ReadinessPolicy
) -> tuple[str | None, ReadinessBasis]:
    ready_events = sorted(_timestamp(item["created_at"]) for item in events if item.get("event") == "ready_for_review")
    if ready_events:
        return _render(ready_events[0]), "observed_event"
    created_at = _timestamp(pull["created_at"])
    if pull.get("draft") is False and _timestamp(pull["updated_at"]) == created_at:
        return _render(created_at), "supported_reconstruction"
    if policy == "created_at_proxy":
        return _render(created_at), "created_at_proxy"
    return None, "unknown"


def _origin(pull: dict[str, object], declarations: tuple[OriginDeclaration, ...]) -> tuple[Origin, OriginBasis]:
    author = pull.get("user")
    if not isinstance(author, dict):
        return "unknown", "missing_author"
    actor_id = author.get("id")
    matches = [item for item in declarations if item.actor_id == actor_id]
    if not matches:
        return "unknown", "unmapped"
    strongest = max(_BASIS_STRENGTH[item.basis] for item in matches)
    strongest_matches = [item for item in matches if _BASIS_STRENGTH[item.basis] == strongest]
    if len({item.origin for item in strongest_matches}) != 1:
        return "unknown", "conflicting_mapping"
    winner = strongest_matches[0]
    return winner.origin, winner.basis


def resolve_attribution(
    pull: dict[str, object],
    events: list[dict[str, object]],
    config: AttributionConfig,
    *,
    lifecycle_complete: bool = True,
) -> Attribution:
    """Resolve one PR without mutating projected source observations."""
    ready_at, readiness_basis = _readiness(pull, events, config.readiness_policy)
    event_names = [item.get("event") for item in events]
    if "reopened" in event_names:
        exclusion: FitExclusion | None = "reopened"
    elif event_names.count("ready_for_review") > 1 or (
        "ready_for_review" in event_names and "converted_to_draft" in event_names
    ):
        exclusion = "repeated_readiness_cycle"
    elif not lifecycle_complete:
        exclusion = "incomplete_lifecycle"
    elif readiness_basis == "unknown":
        exclusion = "unknown_readiness"
    else:
        exclusion = None
    origin, origin_basis = _origin(pull, config.actor_origins)
    return {
        "id": cast(int, pull["id"]),
        "ready_at": ready_at,
        "readiness_basis": readiness_basis,
        "readiness_policy": config.readiness_policy,
        "origin": origin,
        "origin_basis": origin_basis,
        "fit_eligible": exclusion is None,
        "fit_exclusion_reason": exclusion,
        "basis": "derived",
    }
