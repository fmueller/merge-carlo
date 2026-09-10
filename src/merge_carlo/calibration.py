"""Build a provenance-tagged model without inferring active effort from latency."""

import hashlib
import json
import math
import platform
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from merge_carlo import __version__
from merge_carlo.features import FeatureSet
from merge_carlo.simulation.arrivals import WeekTemplate
from merge_carlo.simulation.domain import WorkOrigin

type Basis = Literal["observed", "derived", "proxy", "assumed", "synthetic"]
type EvidenceStatus = Literal["empirically_informed", "exploratory_only", "synthetic_demonstration"]
type CollectionStatus = Literal["complete", "partial", "unavailable", "not_requested"]
type ReadinessPolicy = Literal["strict", "created_at_proxy"]


class _InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class ConstantDuration(_InputModel):
    kind: Literal["constant"]
    seconds: float = Field(gt=0, allow_inf_nan=False)


class LognormalDuration(_InputModel):
    """Median parameterization; sigma is the log-space standard deviation."""

    kind: Literal["lognormal"]
    median_seconds: float = Field(gt=0, allow_inf_nan=False)
    sigma: float = Field(ge=0, allow_inf_nan=False)


class EmpiricalDuration(_InputModel):
    kind: Literal["empirical"]
    seconds: tuple[float, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def finite_positive(self) -> Self:
        if any(not math.isfinite(value) or value <= 0 for value in self.seconds):
            raise ValueError("empirical durations must be finite and positive")
        return self


type DurationDistribution = Annotated[
    ConstantDuration | LognormalDuration | EmpiricalDuration,
    Field(discriminator="kind"),
]


class ReviewEffort(_InputModel):
    """Required active-service assumptions pooled by declared work origin."""

    human: DurationDistribution
    ai: DurationDistribution
    non_ai_automation: DurationDistribution
    unknown: DurationDistribution


class CalibrationAssumptions(_InputModel):
    review_effort: ReviewEffort


class CalibrationCoverage(_InputModel):
    """De-identified dataset coverage supplied by the ingestion/report boundary."""

    dataset_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: str = Field(min_length=1)
    analysis_start: AwareDatetime
    analysis_end: AwareDatetime
    retrieved_at: AwareDatetime
    collection_status: dict[str, CollectionStatus]
    readiness_policy: ReadinessPolicy
    readiness_basis_counts: dict[str, int]
    origin_counts: dict[str, int]
    lifecycle_exclusion_counts: dict[str, int]
    synthetic_data: bool = False

    @model_validator(mode="after")
    def valid_coverage(self) -> Self:
        if self.analysis_start >= self.analysis_end or self.retrieved_at < self.analysis_start:
            raise ValueError("invalid calibration coverage interval")
        count_groups = (self.readiness_basis_counts, self.origin_counts, self.lifecycle_exclusion_counts)
        if any(type(count) is not int or count < 0 for group in count_groups for count in group.values()):
            raise ValueError("coverage counts must be nonnegative integers")
        required_readiness = {"observed_event", "supported_reconstruction", "created_at_proxy", "unknown"}
        required_origins = {origin.value for origin in WorkOrigin}
        required_collections = {"pull_requests", "reviews", "lifecycle_events", "ci_observations"}
        if set(self.readiness_basis_counts) != required_readiness or set(self.origin_counts) != required_origins:
            raise ValueError("coverage must include every readiness basis and work origin")
        if set(self.collection_status) != required_collections:
            raise ValueError("coverage must include every required collection status")
        if sum(self.readiness_basis_counts.values()) != sum(self.origin_counts.values()):
            raise ValueError("readiness and origin coverage totals must match")
        return self


class CalibrationThresholds(_InputModel):
    min_usable_pull_requests: int = Field(default=30, ge=1)
    min_substantive_decisions: int = Field(default=20, ge=1)
    min_complete_weeks: int = Field(default=8, ge=1)
    max_unknown_readiness_fraction: float = Field(default=0.2, ge=0, le=1, allow_inf_nan=False)


@dataclass(frozen=True, slots=True)
class Unavailable:
    value: None
    reason: str


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    value_specification: dict[str, object]
    unit: str
    basis: Basis
    sample_count: int
    missingness_treatment: str
    grouping_rule: str
    fallback_rule: str
    evidence_references: tuple[str, ...]
    confidence_interval: Unavailable


@dataclass(frozen=True, slots=True)
class CalibratedModel:
    schema_version: int
    model_version: str
    feature_version: str
    training_cutoff: datetime
    timezone: str
    dataset_content_hash: str
    assumptions_content_hash: str
    application_version: str
    python_version: str
    dependency_versions: dict[str, str]
    seed: Unavailable
    rng_scheme: Unavailable
    reviewer_roster: Unavailable
    initialization_scheme: Unavailable
    readiness_policy: ReadinessPolicy
    evidence_status: EvidenceStatus
    evidence_flags: tuple[str, ...]
    arrival_templates: tuple[WeekTemplate, ...]
    parameters: tuple[Parameter, ...]


@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    schema_version: int
    training_cutoff: datetime
    readiness_policy: ReadinessPolicy
    usable_pull_requests: int
    substantive_decisions: int
    complete_weeks: int
    unknown_readiness_fraction: float | None
    thresholds: CalibrationThresholds
    evidence_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    model: CalibratedModel
    calibration: CalibrationRecord
    coverage: CalibrationCoverage
    unsupported: dict[str, Unavailable]


def load_assumptions(data: object) -> CalibrationAssumptions:
    """Validate explicit active-effort assumptions with a stable diagnostic."""
    if not isinstance(data, dict) or "review_effort" not in data:
        raise ValueError("required calibration assumptions missing: review_effort")
    try:
        return CalibrationAssumptions.model_validate(data)
    except ValidationError as error:
        text = str(error)
        if "mean_seconds" in text:
            raise ValueError(
                "lognormal requires median_seconds and log-space sigma; mean-and-sigma is ambiguous"
            ) from None
        missing = [".".join(str(part) for part in item["loc"]) for item in error.errors() if item["type"] == "missing"]
        if missing:
            raise ValueError(f"required calibration assumptions missing: {', '.join(missing)}") from None
        raise ValueError("invalid calibration assumptions") from None


def _unavailable(reason: str) -> Unavailable:
    return Unavailable(None, reason)


def _parameter(
    name: str,
    specification: dict[str, object],
    *,
    unit: str,
    basis: Basis,
    sample_count: int,
    missingness: str,
    grouping: str,
    fallback: str,
    references: tuple[str, ...],
    confidence_reason: str = "not_estimated",
) -> Parameter:
    return Parameter(
        name,
        specification,
        unit,
        basis,
        sample_count,
        missingness,
        grouping,
        fallback,
        references,
        _unavailable(confidence_reason),
    )


def _parameters(features: FeatureSet, assumptions: CalibrationAssumptions) -> tuple[Parameter, ...]:
    first_review = tuple(
        row.first_substantive_review_elapsed.total_seconds()
        for row in features.pull_requests
        if row.first_substantive_review_elapsed is not None
    )
    ready_to_merge = tuple(value.total_seconds() for value in features.ready_to_merge.observations)
    prevalence = features.requested_change_prevalence
    parameters = [
        _parameter(
            "arrival_week_templates",
            {"kind": "empirical_week_templates", "weeks": len(features.week_templates)},
            unit="local_week",
            basis="derived",
            sample_count=len(features.week_templates),
            missingness="only complete local calendar weeks retained",
            grouping=f"whole weeks in {features.timezone}",
            fallback="none; no complete weeks is rejected",
            references=("feature_set.week_templates", "specs/v0.1.0.md#empirical-model-and-validation"),
        ),
        _parameter(
            "first_substantive_review_elapsed",
            {"kind": "empirical", "seconds": first_review},
            unit="seconds",
            basis="derived",
            sample_count=len(first_review),
            missingness="missing when no complete qualifying non-author declared-human decision exists",
            grouping="pooled descriptive latency; never active service effort",
            fallback="none",
            references=("feature_set.pull_requests", "docs/feature-builder.md"),
        ),
        _parameter(
            "requested_change_prevalence",
            {
                "kind": "proportion",
                "numerator": prevalence.numerator,
                "denominator": prevalence.denominator,
                "observation_horizon_seconds": prevalence.observation_horizon.total_seconds(),
                "value": prevalence.numerator / prevalence.denominator if prevalence.denominator else None,
            },
            unit="probability",
            basis="derived",
            sample_count=prevalence.denominator,
            missingness="only mature PRs with a first substantive decision inside the declared horizon",
            grouping="first observed decision; not a defect rate",
            fallback="null when denominator is zero",
            references=("feature_set.requested_change_prevalence", "docs/feature-builder.md"),
        ),
        _parameter(
            "ready_to_merge_elapsed",
            {"kind": "empirical", "seconds": ready_to_merge},
            unit="seconds",
            basis="derived",
            sample_count=len(ready_to_merge),
            missingness="completion_conditioned",
            grouping="observed merges only; not an uncensored population distribution",
            fallback="none",
            references=("feature_set.ready_to_merge", "docs/feature-builder.md"),
        ),
    ]
    effort = assumptions.review_effort
    for origin in WorkOrigin:
        distribution = getattr(effort, origin.value)
        parameters.append(
            _parameter(
                f"review_effort.{origin.value}",
                distribution.model_dump(mode="json"),
                unit="active_service_seconds",
                basis="assumed",
                sample_count=len(distribution.seconds) if isinstance(distribution, EmpiricalDuration) else 0,
                missingness="operator supplied; not inferred from elapsed review latency",
                grouping=f"pooled by declared {origin.value} work-origin cohort",
                fallback="none; every cohort assumption is required",
                references=("calibration_assumptions.review_effort", "docs/limitations.md#identifiability"),
                confidence_reason="not_declared",
            )
        )
    return tuple(parameters)


def calibrate_model(
    features: FeatureSet,
    assumptions: CalibrationAssumptions,
    coverage: CalibrationCoverage,
    *,
    thresholds: CalibrationThresholds | None = None,
) -> CalibrationResult:
    """Construct descriptive and assumed parameters at one frozen cutoff."""
    thresholds = thresholds or CalibrationThresholds()
    if not features.week_templates:
        raise ValueError("at least one complete training week is required")
    if (
        features.dataset_content_hash != coverage.dataset_content_hash
        or features.readiness_policy != coverage.readiness_policy
    ):
        raise ValueError("coverage does not match frozen feature source")
    usable = len(features.pull_requests)
    decisions = features.requested_change_prevalence.denominator
    weeks = len(features.week_templates)
    readiness_total = sum(coverage.readiness_basis_counts.values())
    unknown_fraction = coverage.readiness_basis_counts["unknown"] / readiness_total if readiness_total else None
    flags = []
    if usable < thresholds.min_usable_pull_requests:
        flags.append("too_few_usable_pull_requests")
    if decisions < thresholds.min_substantive_decisions:
        flags.append("too_few_substantive_decisions")
    if weeks < thresholds.min_complete_weeks:
        flags.append("insufficient_complete_weeks")
    if unknown_fraction is None or unknown_fraction > thresholds.max_unknown_readiness_fraction:
        flags.append("excessive_unknown_readiness")
    if any(
        coverage.collection_status[name] in {"partial", "unavailable"}
        for name in ("pull_requests", "reviews", "lifecycle_events")
    ):
        flags.append("incomplete_source_collections")
    assumptions_json = json.dumps(assumptions.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    model = CalibratedModel(
        schema_version=1,
        model_version="fifo-v0.1",
        feature_version="features-v1",
        training_cutoff=features.training_cutoff,
        timezone=features.timezone,
        dataset_content_hash=coverage.dataset_content_hash,
        assumptions_content_hash=hashlib.sha256(assumptions_json.encode()).hexdigest(),
        application_version=__version__,
        python_version=platform.python_version(),
        dependency_versions={
            name: version(name) for name in ("numpy", "simpy", "pydantic", "httpx", "pyyaml", "typer")
        },
        seed=_unavailable("not_applicable_to_calibration"),
        rng_scheme=_unavailable("not_applicable_to_calibration"),
        reviewer_roster=_unavailable("downstream_simulation_input"),
        initialization_scheme=_unavailable("downstream_simulation_input"),
        readiness_policy=coverage.readiness_policy,
        evidence_status=(
            "synthetic_demonstration"
            if coverage.synthetic_data
            else "exploratory_only"
            if flags
            else "empirically_informed"
        ),
        evidence_flags=tuple(flags),
        arrival_templates=features.week_templates,
        parameters=_parameters(features, assumptions),
    )
    record = CalibrationRecord(
        schema_version=1,
        training_cutoff=features.training_cutoff,
        readiness_policy=coverage.readiness_policy,
        usable_pull_requests=usable,
        substantive_decisions=decisions,
        complete_weeks=weeks,
        unknown_readiness_fraction=unknown_fraction,
        thresholds=thresholds,
        evidence_flags=tuple(flags),
    )
    unsupported = {
        name: _unavailable("unsupported_in_v0_1")
        for name in ("defect_escape_rate", "security_risk_change", "policy_safety")
    }
    return CalibrationResult(model, record, coverage, unsupported)


def _code(value: object) -> str:
    return str(value).replace("`", "\\`")


def render_model_card(result: CalibrationResult) -> str:
    """Render deterministic evidence claims; unavailable values are explicit."""
    model = result.model
    coverage = result.coverage
    limitation = (
        "This synthetic demonstration is not empirical evidence and does not establish causal or intervention validity."
        if model.evidence_status == "synthetic_demonstration"
        else "This calibration is empirically informed but does not infer active effort from elapsed latency and does "
        "not establish causal or intervention validity."
    )
    lines = [
        "# Model card",
        "",
        "## Identity",
        "",
        f"- Model version: `{model.model_version}`",
        f"- Application version: `{model.application_version}`; schema version: `{model.schema_version}`; "
        f"feature version: `{model.feature_version}`",
        f"- Dataset content hash: `{model.dataset_content_hash}`",
        f"- Assumptions content hash: `{model.assumptions_content_hash}`",
        f"- Training cutoff: `{model.training_cutoff.isoformat()}`; timezone: `{_code(model.timezone)}`",
        f"- Seed: `null` (reason: `{model.seed.reason}`)",
        f"- RNG scheme: `null` (reason: `{model.rng_scheme.reason}`)",
        f"- Python version: `{model.python_version}`",
        f"- Dependency versions: `{json.dumps(model.dependency_versions, sort_keys=True)}`",
        f"- Synthetic data: `{str(coverage.synthetic_data).lower()}`",
        "",
        "## Evidence status",
        "",
        f"`{model.evidence_status}` at the frozen training cutoff; intervention validation is not established.",
        "",
        "## Data coverage",
        "",
        f"- Repository: `{_code(coverage.repository)}`",
        f"- Analysis window: `{coverage.analysis_start.isoformat()}` to `{coverage.analysis_end.isoformat()}`",
        f"- Retrieved at: `{coverage.retrieved_at.isoformat()}`",
        f"- Readiness policy: `{coverage.readiness_policy}`",
        f"- Readiness basis counts: `{json.dumps(coverage.readiness_basis_counts, sort_keys=True)}`",
        f"- Origin counts: `{json.dumps(coverage.origin_counts, sort_keys=True)}`",
        f"- Collection status: `{json.dumps(coverage.collection_status, sort_keys=True)}`",
        f"- Lifecycle exclusions: `{json.dumps(coverage.lifecycle_exclusion_counts, sort_keys=True)}`",
        f"- Complete training weeks: `{result.calibration.complete_weeks}`",
        "",
        "## Parameters",
        "",
    ]
    for parameter in model.parameters:
        interval = parameter.confidence_interval
        lines.extend(
            (
                f"### `{parameter.name}`",
                "",
                f"- Value specification: `{json.dumps(parameter.value_specification, sort_keys=True)}`",
                f"- Unit: `{parameter.unit}`; basis: `{parameter.basis}`; sample count: `{parameter.sample_count}`",
                f"- Missingness: {parameter.missingness_treatment}",
                f"- Grouping: {parameter.grouping_rule}",
                f"- Fallback: {parameter.fallback_rule}",
                f"- Evidence: {', '.join(parameter.evidence_references)}",
                f"- confidence interval: `null` (reason: `{interval.reason}`)",
                "",
            )
        )
    lines.extend(
        (
            "## Workflow assumptions",
            "",
            "CI-before-review, one-required-review, central FIFO scheduling, with active review effort pooled by "
            "declared work-origin cohort.",
            f"- Reviewer roster: `null` (reason: `{model.reviewer_roster.reason}`)",
            f"- Initialization scheme: `null` (reason: `{model.initialization_scheme.reason}`)",
            "Reviewer calendars and downstream scenario choices remain explicit simulation inputs.",
            "",
            "## Evidence flags",
            "",
            *(f"- `{flag}`" for flag in model.evidence_flags),
            *(("- None",) if not model.evidence_flags else ()),
            "",
            "## Unsupported quantities",
            "",
            *(f"- `{name}`: `null` (reason: `{value.reason}`)" for name, value in sorted(result.unsupported.items())),
            "",
            "## Limitations",
            "",
            f"See `docs/limitations.md`. {limitation}",
            "",
        )
    )
    return "\n".join(lines)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def write_calibration(result: CalibrationResult, out: Path) -> None:
    """Atomically publish a model, its calibration record, and model card."""
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError("output directory must be empty or absent")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        model = TypeAdapter(CalibratedModel).dump_python(result.model, mode="json")
        calibration = {
            **TypeAdapter(CalibrationRecord).dump_python(result.calibration, mode="json"),
            "coverage": result.coverage.model_dump(mode="json"),
            "unsupported": TypeAdapter(dict[str, Unavailable]).dump_python(result.unsupported, mode="json"),
        }
        (stage / "model.json").write_text(_json(model), encoding="utf-8")
        (stage / "calibration.json").write_text(_json(calibration), encoding="utf-8")
        (stage / "model-card.md").write_text(render_model_card(result), encoding="utf-8")
        if out.exists():
            out.rmdir()
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
