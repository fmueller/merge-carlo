"""Strict, versioned assumption and scenario configuration contracts."""

import json
import math
import shutil
import tempfile
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from merge_carlo.calibration import DurationDistribution

_MAX_CONFIG_BYTES = 1_000_000
_EFFORT_COMPOSITION = (
    "Effective service is ceil(sampled active-service seconds × effort_multiplier), with a minimum of one second. "
    "The multiplier is an explicit sensitivity assumption, not an observed productivity effect."
)


class _ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class RevisionLoopsConfig(_ConfigModel):
    verification_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    author_response_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    verification_failure_probability: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    first_change_probability: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    repeat_change_probability: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    max_review_visits: int = Field(default=100, strict=True, ge=1)
    max_verification_attempts: int = Field(default=100, strict=True, ge=1)


class AbandonmentConfig(_ConfigModel):
    probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    elapsed_seconds: tuple[float, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def finite_positive_durations(self) -> Self:
        if any(not math.isfinite(value) or value <= 0 for value in self.elapsed_seconds):
            raise ValueError("abandonment durations must be finite and positive")
        return self


class AssumptionSetConfig(_ConfigModel):
    name: str = Field(min_length=1)
    active_service: DurationDistribution = Field(description="Active human-review effort before sensitivity scaling.")
    effort_multiplier: float = Field(default=1, gt=0, allow_inf_nan=False, description=_EFFORT_COMPOSITION)
    loops: RevisionLoopsConfig = RevisionLoopsConfig()
    abandonment: AbandonmentConfig | None = None
    coordination_seconds: float = Field(
        default=0,
        ge=0,
        allow_inf_nan=False,
        description="Elapsed coordination delay; zero is permitted because this is not active review service.",
    )


class AssumptionConfig(_ConfigModel):
    schema_version: Literal[1]
    assumptions: tuple[AssumptionSetConfig, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        names = tuple(item.name for item in self.assumptions)
        if len(set(names)) != len(names):
            raise ValueError("assumption names must be unique")
        return self


class AdditiveDemandConfig(_ConfigModel):
    kind: Literal["additive_ai"]
    fraction: float = Field(ge=0, allow_inf_nan=False)


class ReplacementDemandConfig(_ConfigModel):
    kind: Literal["replacement_ai"]
    fraction: float = Field(ge=0, le=1, allow_inf_nan=False)


type DemandConfig = Annotated[AdditiveDemandConfig | ReplacementDemandConfig, Field(discriminator="kind")]


class WeeklyWindowConfig(_ConfigModel):
    name: str = Field(min_length=1)
    weekday: int = Field(strict=True, ge=0, le=6, description="Monday is 0 and Sunday is 6.")
    start: time = Field(json_schema_extra={"pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?$"})
    end: time = Field(json_schema_extra={"pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?$"})

    @model_validator(mode="after")
    def distinct_boundaries(self) -> Self:
        if self.start.tzinfo is not None or self.end.tzinfo is not None or self.start == self.end:
            raise ValueError("weekly window boundaries must be naive and distinct")
        return self


class AbsenceConfig(_ConfigModel):
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def normalize_fixed_offset(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        return value if offset is None else value.replace(tzinfo=timezone(offset))

    @model_validator(mode="after")
    def ordered_boundaries(self) -> Self:
        if (self.start.tzinfo is None) != (self.end.tzinfo is None) or self.end <= self.start:
            raise ValueError("absence boundaries must have matching timezone form and increasing order")
        return self


class CalendarConfig(_ConfigModel):
    name: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    windows: tuple[WeeklyWindowConfig, ...]
    absences: tuple[AbsenceConfig, ...] = ()

    @model_validator(mode="after")
    def valid_calendar(self) -> Self:
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown timezone") from None
        names = tuple(window.name for window in self.windows)
        if len(set(names)) != len(names):
            raise ValueError("weekly window names must be unique")
        return self


class ReviewerAbsencesConfig(_ConfigModel):
    reviewer: str = Field(min_length=1)
    absences: tuple[AbsenceConfig, ...] = Field(min_length=1)


class ReviewBypassConfig(_ConfigModel):
    eligible_fraction: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    audit_fraction: float = Field(ge=0, le=1, allow_inf_nan=False)


class ScenarioEntryConfig(_ConfigModel):
    name: str = Field(min_length=1)
    demand: DemandConfig | None = None
    calendars: tuple[CalendarConfig, ...] = ()
    absences: tuple[ReviewerAbsencesConfig, ...] = ()
    bypass: ReviewBypassConfig | None = None

    @model_validator(mode="after")
    def unique_overrides(self) -> Self:
        for names in (
            tuple(calendar.name for calendar in self.calendars),
            tuple(entry.reviewer for entry in self.absences),
        ):
            if len(set(names)) != len(names):
                raise ValueError("scenario override names must be unique")
        return self


class ScenarioConfig(_ConfigModel):
    schema_version: Literal[1]
    scenarios: tuple[ScenarioEntryConfig, ...]

    @model_validator(mode="after")
    def unique_nonbaseline_names(self) -> Self:
        names = tuple(item.name for item in self.scenarios)
        if "baseline" in names or len(set(names)) != len(names):
            raise ValueError("scenario names must be unique and cannot be baseline")
        return self


def _load_config[ConfigT: BaseModel](path: Path, model: type[ConfigT]) -> ConfigT:
    try:
        with path.open("rb") as stream:
            raw = stream.read(_MAX_CONFIG_BYTES + 1)
        if len(raw) > _MAX_CONFIG_BYTES:
            raise ValueError
        return model.model_validate(yaml.safe_load(raw.decode("utf-8")))
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, ValueError):
        raise ValueError("invalid configuration") from None


def load_assumption_config(path: Path) -> AssumptionConfig:
    """Load bounded, data-only assumption YAML."""
    return _load_config(path, AssumptionConfig)


def load_scenario_config(path: Path) -> ScenarioConfig:
    """Load bounded, data-only scenario YAML."""
    return _load_config(path, ScenarioConfig)


def active_service_seconds(sampled_seconds: float, effort_multiplier: float) -> int:
    """Compose explicit effort sensitivity, then round active service up."""
    effective = sampled_seconds * effort_multiplier
    if (
        isinstance(sampled_seconds, bool)
        or isinstance(effort_multiplier, bool)
        or not math.isfinite(effective)
        or sampled_seconds <= 0
        or effort_multiplier <= 0
    ):
        raise ValueError("active service and multiplier must be finite and positive")
    return max(1, math.ceil(effective))


def _schema(model: type[BaseModel], identity: str) -> str:
    schema = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://merge-carlo.dev/schemas/v1/{identity}.schema.json"
    return json.dumps(schema, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def export_schemas(out: Path) -> None:
    """Atomically write deterministic version-1 configuration schemas."""
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError("output directory must be empty or absent")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        (stage / "assumptions.schema.json").write_text(_schema(AssumptionConfig, "assumptions"), encoding="utf-8")
        (stage / "scenarios.schema.json").write_text(_schema(ScenarioConfig, "scenarios"), encoding="utf-8")
        if out.exists():
            out.rmdir()
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
