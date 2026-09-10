"""Chronological held-out descriptive validation of persisted replay outcomes."""

import hashlib
import json
import math
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from pydantic.dataclasses import dataclass

from merge_carlo.calibration import Unavailable
from merge_carlo.reporting import markdown, wilson
from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import PullRequest, PullRequestState, WorkOrigin
from merge_carlo.simulation.engine import Reviewer, RevisionLoops, run_fifo
from merge_carlo.simulation.randomness import random_stream

type ValidationStatus = Literal["pass", "fail", "insufficient_evidence"]
type ValidationProtocol = Literal["held_out", "in_sample_diagnostic"]
type CompletionCategory = Literal["merged", "closed_without_merge", "not_completed"]
type ValidationMetric = Literal[
    "reviewed_within_48_hours_share",
    "merged_within_7_days_share",
    "first_review_median_seconds",
    "weekly_merge_count",
    "initialization_backlog",
]


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ValidationThresholds:
    min_mature_pull_requests: int = 20
    min_replications: int = 20
    reviewed_share_tolerance: float = 0.1
    merged_share_tolerance: float = 0.1
    first_review_median_tolerance_seconds: float = 14_400
    weekly_merges_tolerance: float = 2.0
    initialization_backlog_tolerance: float = 5.0

    def __post_init__(self) -> None:
        if type(self.min_mature_pull_requests) is not int or self.min_mature_pull_requests < 1:
            raise ValueError("minimum mature pull requests must be a positive integer")
        if type(self.min_replications) is not int or self.min_replications < 1:
            raise ValueError("minimum replications must be a positive integer")
        probabilities = (self.reviewed_share_tolerance, self.merged_share_tolerance)
        nonnegative = (
            self.first_review_median_tolerance_seconds,
            self.weekly_merges_tolerance,
            self.initialization_backlog_tolerance,
        )
        if any(isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities):
            raise ValueError("share tolerances must be finite probabilities")
        if any(isinstance(value, bool) or not math.isfinite(value) or value < 0 for value in nonnegative):
            raise ValueError("validation tolerances must be finite and nonnegative")


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ObservedOutcomes:
    """Held-out outcomes inspected only after the model and split are frozen."""

    reviewed_within_48_hours_successes: int
    reviewed_mature_pull_requests: int
    merged_within_7_days_successes: int
    merged_mature_pull_requests: int
    first_review_elapsed_seconds: tuple[float, ...]
    weekly_merge_counts: tuple[int, ...]
    initial_backlog: int

    def __post_init__(self) -> None:
        for successes, cohort in (
            (self.reviewed_within_48_hours_successes, self.reviewed_mature_pull_requests),
            (self.merged_within_7_days_successes, self.merged_mature_pull_requests),
        ):
            _validate_count(cohort, "mature pull-request count")
            if type(successes) is not int or not 0 <= successes <= cohort:
                raise ValueError("observed horizon successes must be within their mature cohort")
        _validate_samples(self.first_review_elapsed_seconds, "first-review elapsed times", empty=True)
        _validate_counts(self.weekly_merge_counts, "weekly merge counts")
        _validate_count(self.initial_backlog, "initial backlog")


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ReplayOutcomes:
    """One frozen-model replay using held-out arrival timestamps and known-at-arrival attributes."""

    reviewed_within_48_hours_successes: int
    reviewed_mature_pull_requests: int
    merged_within_7_days_successes: int
    merged_mature_pull_requests: int
    first_review_median_seconds: float | None
    first_review_completions: int
    weekly_merge_counts: tuple[int, ...]
    initial_backlog: int

    def __post_init__(self) -> None:
        for successes, cohort, name in (
            (
                self.reviewed_within_48_hours_successes,
                self.reviewed_mature_pull_requests,
                "reviewed mature cohort",
            ),
            (self.merged_within_7_days_successes, self.merged_mature_pull_requests, "merged mature cohort"),
        ):
            _validate_count(cohort, name)
            if type(successes) is not int or not 0 <= successes <= cohort:
                raise ValueError("replay horizon successes must be within their mature cohort")
        for value, name in (
            (self.first_review_completions, "first-review completions"),
            (self.initial_backlog, "initial backlog"),
        ):
            _validate_count(value, name)
        if self.first_review_median_seconds is not None and (
            isinstance(self.first_review_median_seconds, bool)
            or not math.isfinite(self.first_review_median_seconds)
            or self.first_review_median_seconds < 0
        ):
            raise ValueError("first-review median must be finite and nonnegative")
        if (self.first_review_median_seconds is None) != (self.first_review_completions == 0):
            raise ValueError("first-review median requires a nonempty completion cohort")
        _validate_counts(self.weekly_merge_counts, "weekly merge counts")


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ElapsedDelayObservation:
    """One joint historical delay/outcome record for the descriptive benchmark."""

    ready_at: datetime
    observed_until: datetime
    first_review_elapsed_seconds: float | None
    completion_category: CompletionCategory
    completion_elapsed_seconds: float | None

    def __post_init__(self) -> None:
        if any(value.tzinfo is None or value.utcoffset() is None for value in (self.ready_at, self.observed_until)):
            raise ValueError("benchmark observation timestamps must be timezone aware")
        ready_at = self.ready_at.astimezone(UTC)
        observed_until = self.observed_until.astimezone(UTC)
        if ready_at >= observed_until:
            raise ValueError("benchmark observation interval must be positive")
        if self.first_review_elapsed_seconds is not None:
            _validate_samples((self.first_review_elapsed_seconds,), "first-review elapsed times")
        if self.completion_category == "not_completed":
            if self.completion_elapsed_seconds is not None:
                raise ValueError("not-completed observations cannot have a completion delay")
        elif self.completion_elapsed_seconds is None:
            raise ValueError("completed observations require a completion delay")
        else:
            _validate_samples((self.completion_elapsed_seconds,), "completion elapsed times")
        if (
            self.first_review_elapsed_seconds is not None
            and self.completion_elapsed_seconds is not None
            and self.first_review_elapsed_seconds > self.completion_elapsed_seconds
        ):
            raise ValueError("first review cannot occur after completion")
        observed_seconds = (observed_until - ready_at).total_seconds()
        if self.first_review_elapsed_seconds is not None and self.first_review_elapsed_seconds > observed_seconds:
            raise ValueError("first review falls outside the benchmark observation interval")
        if self.completion_elapsed_seconds is not None and self.completion_elapsed_seconds > observed_seconds:
            raise ValueError("completion falls outside the benchmark observation interval")


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class CompletionCategoryCounts:
    merged: int
    closed_without_merge: int
    not_completed: int

    def __post_init__(self) -> None:
        for value in (self.merged, self.closed_without_merge, self.not_completed):
            _validate_count(value, "benchmark completion-category count")


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class DelayBenchmarkReplication:
    outcomes: ReplayOutcomes
    completion_categories: CompletionCategoryCounts


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class DelayBenchmark:
    replications: tuple[DelayBenchmarkReplication, ...]
    observations_content_hash: str
    label: Literal["descriptive_reference_not_intervention_model"] = "descriptive_reference_not_intervention_model"
    capacity_queue: Literal[False] = False


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class HeldOutEvidence:
    """Frozen split plus outcomes from exact-timestamp held-out replay."""

    model_version: str
    dataset_content_hash: str
    fitting_interval_start: datetime
    training_cutoff: datetime
    validation_interval_start: datetime
    validation_interval_end: datetime
    observed: ObservedOutcomes
    replay_replications: tuple[ReplayOutcomes, ...]
    delay_benchmark: DelayBenchmark
    model_content_hash: str = "0" * 64
    replay_arrivals_content_hash: str = "0" * 64
    thresholds: ValidationThresholds = ValidationThresholds()
    in_sample_diagnostic: bool = False


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ReplayArrival:
    """The complete known-at-arrival replay feature boundary."""

    pr_id: str
    author_id: str
    origin: WorkOrigin
    ready_at: datetime


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ReplayDuty:
    reviewer_id: str
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class FrozenReplayModel:
    model_version: str
    timezone: str
    service_seconds: float
    verification_seconds: float = 0
    author_response_seconds: float = 0
    verification_failure_probability: float = 0
    first_change_probability: float = 0
    repeat_change_probability: float = 0
    max_review_visits: int = 100
    max_verification_attempts: int = 100
    coordination_seconds: float = 0

    def loops(self) -> RevisionLoops:
        return RevisionLoops(
            self.verification_seconds,
            self.author_response_seconds,
            self.verification_failure_probability,
            self.first_change_probability,
            self.repeat_change_probability,
            self.max_review_visits,
            self.max_verification_attempts,
        )


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class ValidationInput:
    dataset_content_hash: str
    fitting_interval_start: datetime
    training_cutoff: datetime
    validation_interval_start: datetime
    validation_interval_end: datetime
    observed: ObservedOutcomes
    model: FrozenReplayModel
    arrivals: tuple[ReplayArrival, ...]
    benchmark_observations: tuple[ElapsedDelayObservation, ...]
    reviewer_duty: tuple[ReplayDuty, ...]
    root_seed: int
    replications: int
    thresholds: ValidationThresholds = ValidationThresholds()
    in_sample_diagnostic: bool = False


class _ResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1


class Estimate(_ResultModel):
    value: float | None
    low: float | None
    high: float | None
    sample_size: int = Field(ge=0, strict=True)
    reason: str | None = None

    @model_validator(mode="after")
    def valid_estimate(self) -> Self:
        if self.value is None:
            if self.low is not None or self.high is not None or self.reason is None:
                raise ValueError("undefined estimate requires null bounds and a reason")
        elif (
            self.low is None
            or self.high is None
            or self.reason is not None
            or not all(math.isfinite(value) for value in (self.low, self.value, self.high))
            or not self.low <= self.value <= self.high
        ):
            raise ValueError("defined estimate requires finite ordered values")
        return self


class ValidationGate(_ResultModel):
    metric: ValidationMetric
    observed: Estimate
    simulated: Estimate
    observed_cohort_size: int = Field(ge=0, strict=True)
    simulated_cohort_sizes: tuple[int, ...]
    absolute_error: float | None
    tolerance: float
    passed: bool | None


class BenchmarkComparison(_ResultModel):
    metric: ValidationMetric
    observed: Estimate
    mechanistic: Estimate
    elapsed_delay_benchmark: Estimate
    mechanistic_absolute_error: float | None
    benchmark_absolute_error: float | None
    better_description: Literal["mechanistic", "elapsed_delay_benchmark", "tie", "unavailable"]


class ValidationResult(_ResultModel):
    status: ValidationStatus
    protocol: ValidationProtocol
    model_version: str
    dataset_content_hash: str
    model_content_hash: str
    replay_arrivals_content_hash: str
    training_cutoff: AwareDatetime
    validation_interval_start: AwareDatetime
    validation_interval_end: AwareDatetime
    thresholds: dict[str, int | float]
    observed_mature_pull_requests: int
    replay_replications: int
    evidence_flags: tuple[str, ...]
    gates: tuple[ValidationGate, ...]
    benchmark_label: Literal["descriptive_reference_not_intervention_model"]
    benchmark_capacity_queue: Literal[False]
    benchmark_observations_content_hash: str
    benchmark_completion_categories: tuple[CompletionCategoryCounts, ...]
    benchmark_comparison: tuple[BenchmarkComparison, ...]
    initialization_discrepancy: Estimate
    absolute_backlog_forecast_supported: bool
    unsupported: dict[str, Unavailable]


def _validate_count(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _validate_counts(values: tuple[int, ...], name: str) -> None:
    if not values or any(type(value) is not int or value < 0 for value in values):
        raise ValueError(f"{name} must be nonempty nonnegative integers")


def _validate_samples(values: tuple[float, ...], name: str, *, empty: bool = False) -> None:
    if (not values and not empty) or any(
        isinstance(value, bool) or not math.isfinite(value) or value < 0 for value in values
    ):
        raise ValueError(f"{name} must be nonempty finite nonnegative values")


def _content_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _validate_split(
    fitting_start: datetime,
    training_cutoff: datetime,
    validation_start: datetime,
    validation_end: datetime,
    in_sample: bool,
) -> None:
    times = (fitting_start, training_cutoff, validation_start, validation_end)
    if any(value.tzinfo is None or value.utcoffset() is None for value in times):
        raise ValueError("validation timestamps must be timezone aware")
    if not fitting_start < training_cutoff:
        raise ValueError("invalid fitting interval")
    if not validation_start < validation_end:
        raise ValueError("invalid validation interval")
    if validation_start < training_cutoff and not in_sample:
        raise ValueError("validation interval overlaps parameter fitting")


def load_validation_evidence(path: Path) -> HeldOutEvidence:
    """Read one bounded, versioned offline validation input."""
    with path.open("rb") as source:
        payload = source.read(16 * 1024 * 1024 + 1)
    if len(payload) > 16 * 1024 * 1024:
        raise ValueError("validation evidence exceeds 16 MiB")
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("invalid validation evidence") from None
    if not isinstance(data, dict) or data.pop("schema_version", None) != 1:
        raise ValueError("unsupported validation evidence schema")
    try:
        request = TypeAdapter(ValidationInput).validate_json(json.dumps(data), strict=True)
    except ValueError:
        raise ValueError("invalid validation evidence") from None
    return replay_held_out(request)


def _weekly_counts(event_seconds: tuple[float, ...], start: datetime, end: datetime, timezone: str) -> tuple[int, ...]:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise ValueError("invalid replay timezone") from None
    keys: list[tuple[int, int]] = []
    day = start.astimezone(zone).date()
    last = (end - timedelta(microseconds=1)).astimezone(zone).date()
    while day <= last:
        key = day.isocalendar()[:2]
        if key not in keys:
            keys.append(key)
        day += timedelta(days=1)
    counts = dict.fromkeys(keys, 0)
    for elapsed in event_seconds:
        key = (start + timedelta(seconds=elapsed)).astimezone(zone).date().isocalendar()[:2]
        if key in counts:
            counts[key] += 1
    return tuple(counts.values())


def replay_elapsed_delay_benchmark(request: ValidationInput) -> DelayBenchmark:
    """Resample joint historical delays onto held-out arrivals without a capacity queue."""
    if not request.benchmark_observations:
        raise ValueError("elapsed-delay benchmark observations must be nonempty")
    fitting_start = request.fitting_interval_start.astimezone(UTC)
    training_cutoff = request.training_cutoff.astimezone(UTC)
    if any(
        row.ready_at.astimezone(UTC) < fitting_start or row.observed_until.astimezone(UTC) > training_cutoff
        for row in request.benchmark_observations
    ):
        raise ValueError("benchmark observations must be frozen within the fitting interval")
    if any(
        row.observed_until.astimezone(UTC) - row.ready_at.astimezone(UTC) < timedelta(days=7)
        for row in request.benchmark_observations
    ):
        raise ValueError("benchmark observations require seven-day follow-up")
    start = request.validation_interval_start.astimezone(UTC)
    end = request.validation_interval_end.astimezone(UTC)
    span_seconds = (end - start).total_seconds()
    replications: list[DelayBenchmarkReplication] = []
    for replication in range(request.replications):
        stream = random_stream(request.root_seed, replication, "elapsed-delay-benchmark")
        sampled = tuple(
            request.benchmark_observations[int(index)]
            for index in stream.integers(0, len(request.benchmark_observations), size=len(request.arrivals))
        )
        ready_seconds = tuple((row.ready_at.astimezone(UTC) - start).total_seconds() for row in request.arrivals)
        review_delays = tuple(
            observation.first_review_elapsed_seconds
            for ready, observation in zip(ready_seconds, sampled, strict=True)
            if observation.first_review_elapsed_seconds is not None
            and ready + observation.first_review_elapsed_seconds <= span_seconds
        )
        reviewed_mature = tuple(
            (ready, observation)
            for ready, observation in zip(ready_seconds, sampled, strict=True)
            if ready + 48 * 3600 <= span_seconds
        )
        merged_mature = tuple(
            (ready, observation)
            for ready, observation in zip(ready_seconds, sampled, strict=True)
            if ready + 7 * 86400 <= span_seconds
        )
        merged_at = tuple(
            ready + observation.completion_elapsed_seconds
            for ready, observation in zip(ready_seconds, sampled, strict=True)
            if observation.completion_category == "merged"
            and observation.completion_elapsed_seconds is not None
            and ready + observation.completion_elapsed_seconds < span_seconds
        )
        categories = CompletionCategoryCounts(
            sum(row.completion_category == "merged" for row in sampled),
            sum(row.completion_category == "closed_without_merge" for row in sampled),
            sum(row.completion_category == "not_completed" for row in sampled),
        )
        replications.append(
            DelayBenchmarkReplication(
                ReplayOutcomes(
                    sum(
                        observation.first_review_elapsed_seconds is not None
                        and observation.first_review_elapsed_seconds <= 48 * 3600
                        for _, observation in reviewed_mature
                    ),
                    len(reviewed_mature),
                    sum(
                        observation.completion_category == "merged"
                        and observation.completion_elapsed_seconds is not None
                        and observation.completion_elapsed_seconds <= 7 * 86400
                        for _, observation in merged_mature
                    ),
                    len(merged_mature),
                    float(median(review_delays)) if review_delays else None,
                    len(review_delays),
                    _weekly_counts(merged_at, start, end, request.model.timezone),
                    0,
                ),
                categories,
            )
        )
    observations = TypeAdapter(tuple[ElapsedDelayObservation, ...]).dump_python(
        request.benchmark_observations, mode="json"
    )
    return DelayBenchmark(tuple(replications), _content_hash(observations))


def replay_held_out(request: ValidationInput) -> HeldOutEvidence:
    """Replay exact held-out arrivals through the frozen FIFO model."""
    _validate_split(
        request.fitting_interval_start,
        request.training_cutoff,
        request.validation_interval_start,
        request.validation_interval_end,
        request.in_sample_diagnostic,
    )
    if not request.model.model_version:
        raise ValueError("model version must be nonempty")
    if len(request.dataset_content_hash) != 64 or any(
        character not in "0123456789abcdef" for character in request.dataset_content_hash
    ):
        raise ValueError("invalid dataset content hash")
    start = request.validation_interval_start.astimezone(UTC)
    end = request.validation_interval_end.astimezone(UTC)
    span = UTCInterval(start, end)
    if type(request.root_seed) is not int or request.root_seed < 0:
        raise ValueError("root seed must be a nonnegative integer")
    if type(request.replications) is not int or not 1 <= request.replications <= 10_000:
        raise ValueError("replications must be between one and 10000")
    if not request.arrivals or len({row.pr_id for row in request.arrivals}) != len(request.arrivals):
        raise ValueError("replay arrivals must be nonempty with unique identifiers")
    if any(
        row.ready_at.tzinfo is None
        or row.ready_at.utcoffset() is None
        or not start <= row.ready_at.astimezone(UTC) < end
        for row in request.arrivals
    ):
        raise ValueError("replay arrivals must fall within the validation interval")
    proposals = tuple(
        PullRequest(
            row.pr_id,
            row.author_id,
            row.origin,
            (row.ready_at.astimezone(UTC) - start).total_seconds(),
        )
        for row in request.arrivals
    )
    by_reviewer: dict[str, list[UTCInterval]] = {}
    for duty in request.reviewer_duty:
        if any(value.tzinfo is None or value.utcoffset() is None for value in (duty.start, duty.end)):
            raise ValueError("reviewer duty must be timezone aware")
        by_reviewer.setdefault(duty.reviewer_id, []).append(
            UTCInterval(duty.start.astimezone(UTC), duty.end.astimezone(UTC))
        )
    reviewers = tuple(
        Reviewer(name, tuple(sorted(intervals, key=lambda interval: interval.start)))
        for name, intervals in sorted(by_reviewer.items())
    )
    replayed = []
    for replication in range(request.replications):
        result = run_fifo(
            proposals,
            reviewers,
            span=span,
            service_seconds=request.model.service_seconds,
            loops=request.model.loops(),
            coordination_seconds=request.model.coordination_seconds,
            root_seed=request.root_seed,
            replication=replication,
        )
        if result.engine_truncated:
            continue
        reviewed = tuple(pull for pull in result.pull_requests if pull.ready_at + 48 * 3600 <= span.seconds)
        merged = tuple(pull for pull in result.pull_requests if pull.ready_at + 7 * 86400 <= span.seconds)
        delays = tuple(
            pull.first_review_at - pull.ready_at for pull in result.pull_requests if pull.first_review_at is not None
        )
        replayed.append(
            ReplayOutcomes(
                sum(
                    pull.first_review_at is not None and pull.first_review_at <= pull.ready_at + 48 * 3600
                    for pull in reviewed
                ),
                len(reviewed),
                sum(
                    pull.state is PullRequestState.MERGED
                    and pull.terminal_at is not None
                    and pull.terminal_at <= pull.ready_at + 7 * 86400
                    for pull in merged
                ),
                len(merged),
                float(median(delays)) if delays else None,
                len(delays),
                _weekly_counts(
                    tuple(
                        pull.terminal_at
                        for pull in result.pull_requests
                        if pull.state is PullRequestState.MERGED and pull.terminal_at is not None
                    ),
                    start,
                    end,
                    request.model.timezone,
                ),
                0,
            )
        )
    model_value = TypeAdapter(FrozenReplayModel).dump_python(request.model, mode="json")
    model_value["reviewer_duty"] = TypeAdapter(tuple[ReplayDuty, ...]).dump_python(request.reviewer_duty, mode="json")
    arrivals_value = TypeAdapter(tuple[ReplayArrival, ...]).dump_python(request.arrivals, mode="json")
    benchmark = replay_elapsed_delay_benchmark(request)
    return HeldOutEvidence(
        request.model.model_version,
        request.dataset_content_hash,
        request.fitting_interval_start,
        request.training_cutoff,
        request.validation_interval_start,
        request.validation_interval_end,
        request.observed,
        tuple(replayed),
        benchmark,
        _content_hash(model_value),
        _content_hash(arrivals_value),
        request.thresholds,
        request.in_sample_diagnostic,
    )


def _quantiles(values: tuple[float, ...]) -> Estimate:
    if not values:
        return Estimate(value=None, low=None, high=None, sample_size=0, reason="no_defined_observations")
    return Estimate(
        value=float(median(values)),
        low=float(np.quantile(values, 0.05)),
        high=float(np.quantile(values, 0.95)),
        sample_size=len(values),
    )


def _proportion(successes: int, trials: int) -> Estimate:
    probability = wilson(successes, trials)
    return Estimate(
        value=probability.estimate.value,
        low=probability.low,
        high=probability.high,
        sample_size=trials,
        reason=probability.estimate.reason,
    )


def _gate(
    metric: ValidationMetric,
    observed: Estimate,
    simulated: Estimate,
    observed_cohort_size: int,
    simulated_cohort_sizes: tuple[int, ...],
    tolerance: float,
    evaluate: bool,
) -> ValidationGate:
    error = (
        abs(observed.value - simulated.value) if observed.value is not None and simulated.value is not None else None
    )
    return ValidationGate(
        metric=metric,
        observed=observed,
        simulated=simulated,
        observed_cohort_size=observed_cohort_size,
        simulated_cohort_sizes=simulated_cohort_sizes,
        absolute_error=error,
        tolerance=tolerance,
        passed=error <= tolerance if evaluate and error is not None else None,
    )


def _benchmark_estimates(replications: tuple[DelayBenchmarkReplication, ...]) -> dict[ValidationMetric, Estimate]:
    outcomes = tuple(row.outcomes for row in replications)
    return {
        "reviewed_within_48_hours_share": _quantiles(
            tuple(
                row.reviewed_within_48_hours_successes / row.reviewed_mature_pull_requests
                for row in outcomes
                if row.reviewed_mature_pull_requests
            )
        ),
        "merged_within_7_days_share": _quantiles(
            tuple(
                row.merged_within_7_days_successes / row.merged_mature_pull_requests
                for row in outcomes
                if row.merged_mature_pull_requests
            )
        ),
        "first_review_median_seconds": _quantiles(
            tuple(row.first_review_median_seconds for row in outcomes if row.first_review_median_seconds is not None)
        ),
        "weekly_merge_count": _quantiles(tuple(float(median(row.weekly_merge_counts)) for row in outcomes)),
    }


def _benchmark_comparison(
    gates: tuple[ValidationGate, ...], benchmark: DelayBenchmark
) -> tuple[BenchmarkComparison, ...]:
    benchmark_estimates = _benchmark_estimates(benchmark.replications)
    comparisons = []
    for gate in gates:
        if gate.metric not in benchmark_estimates:
            continue
        benchmark_estimate = benchmark_estimates[gate.metric]
        benchmark_error = (
            abs(gate.observed.value - benchmark_estimate.value)
            if gate.observed.value is not None and benchmark_estimate.value is not None
            else None
        )
        mechanistic_error = gate.absolute_error
        if benchmark_error is None or mechanistic_error is None:
            better: Literal["mechanistic", "elapsed_delay_benchmark", "tie", "unavailable"] = "unavailable"
        elif benchmark_error < mechanistic_error:
            better = "elapsed_delay_benchmark"
        elif mechanistic_error < benchmark_error:
            better = "mechanistic"
        else:
            better = "tie"
        comparisons.append(
            BenchmarkComparison(
                metric=gate.metric,
                observed=gate.observed,
                mechanistic=gate.simulated,
                elapsed_delay_benchmark=benchmark_estimate,
                mechanistic_absolute_error=mechanistic_error,
                benchmark_absolute_error=benchmark_error,
                better_description=better,
            )
        )
    return tuple(comparisons)


def run_validation(evidence: HeldOutEvidence) -> ValidationResult:
    """Apply declared descriptive gates to a frozen chronological replay."""
    _validate_split(
        evidence.fitting_interval_start,
        evidence.training_cutoff,
        evidence.validation_interval_start,
        evidence.validation_interval_end,
        evidence.in_sample_diagnostic,
    )
    if not evidence.model_version:
        raise ValueError("model version must be nonempty")
    if len(evidence.dataset_content_hash) != 64 or any(
        character not in "0123456789abcdef" for character in evidence.dataset_content_hash
    ):
        raise ValueError("invalid dataset content hash")

    observed = evidence.observed
    replications = evidence.replay_replications
    flags = []
    if min(observed.reviewed_mature_pull_requests, observed.merged_mature_pull_requests) < (
        evidence.thresholds.min_mature_pull_requests
    ):
        flags.append("too_few_mature_pull_requests")
    if len(replications) < evidence.thresholds.min_replications:
        flags.append("too_few_replay_replications")
    if not observed.first_review_elapsed_seconds:
        flags.append("no_observed_first_review_completions")
    defined_reviews = sum(row.first_review_median_seconds is not None for row in replications)
    if replications and not defined_reviews:
        flags.append("no_simulated_first_review_completions")
    elif defined_reviews < evidence.thresholds.min_replications:
        flags.append("too_few_defined_first_review_replications")
    if any(not row.reviewed_mature_pull_requests or not row.merged_mature_pull_requests for row in replications):
        flags.append("empty_replay_mature_cohort")
    evaluate = not flags

    reviewed = _gate(
        "reviewed_within_48_hours_share",
        _proportion(observed.reviewed_within_48_hours_successes, observed.reviewed_mature_pull_requests),
        _quantiles(
            tuple(
                row.reviewed_within_48_hours_successes / row.reviewed_mature_pull_requests
                for row in replications
                if row.reviewed_mature_pull_requests
            )
        ),
        observed.reviewed_mature_pull_requests,
        tuple(row.reviewed_mature_pull_requests for row in replications),
        evidence.thresholds.reviewed_share_tolerance,
        evaluate,
    )
    merged = _gate(
        "merged_within_7_days_share",
        _proportion(observed.merged_within_7_days_successes, observed.merged_mature_pull_requests),
        _quantiles(
            tuple(
                row.merged_within_7_days_successes / row.merged_mature_pull_requests
                for row in replications
                if row.merged_mature_pull_requests
            )
        ),
        observed.merged_mature_pull_requests,
        tuple(row.merged_mature_pull_requests for row in replications),
        evidence.thresholds.merged_share_tolerance,
        evaluate,
    )
    review_elapsed = _gate(
        "first_review_median_seconds",
        _quantiles(observed.first_review_elapsed_seconds),
        _quantiles(
            tuple(
                row.first_review_median_seconds for row in replications if row.first_review_median_seconds is not None
            )
        ),
        len(observed.first_review_elapsed_seconds),
        tuple(row.first_review_completions for row in replications),
        evidence.thresholds.first_review_median_tolerance_seconds,
        evaluate,
    )
    weekly_merges = _gate(
        "weekly_merge_count",
        _quantiles(tuple(float(value) for value in observed.weekly_merge_counts)),
        _quantiles(tuple(float(median(row.weekly_merge_counts)) for row in replications)),
        len(observed.weekly_merge_counts),
        tuple(len(row.weekly_merge_counts) for row in replications),
        evidence.thresholds.weekly_merges_tolerance,
        evaluate,
    )
    initialization = _gate(
        "initialization_backlog",
        Estimate(
            value=float(observed.initial_backlog),
            low=float(observed.initial_backlog),
            high=float(observed.initial_backlog),
            sample_size=1,
        ),
        _quantiles(tuple(float(row.initial_backlog) for row in replications)),
        1,
        tuple(1 for _ in replications),
        evidence.thresholds.initialization_backlog_tolerance,
        evaluate,
    )
    gates = (reviewed, merged, review_elapsed, weekly_merges, initialization)
    if flags:
        status: ValidationStatus = "insufficient_evidence"
    elif all(gate.passed for gate in gates):
        status = "pass"
    else:
        status = "fail"
    discrepancy = Estimate(
        value=initialization.absolute_error,
        low=None if initialization.absolute_error is None else initialization.absolute_error,
        high=None if initialization.absolute_error is None else initialization.absolute_error,
        sample_size=initialization.simulated.sample_size,
        reason="no_defined_observations" if initialization.absolute_error is None else None,
    )
    return ValidationResult(
        status=status,
        protocol="in_sample_diagnostic" if evidence.in_sample_diagnostic else "held_out",
        model_version=evidence.model_version,
        dataset_content_hash=evidence.dataset_content_hash,
        model_content_hash=evidence.model_content_hash,
        replay_arrivals_content_hash=evidence.replay_arrivals_content_hash,
        training_cutoff=evidence.training_cutoff,
        validation_interval_start=evidence.validation_interval_start,
        validation_interval_end=evidence.validation_interval_end,
        thresholds=TypeAdapter(ValidationThresholds).dump_python(evidence.thresholds),
        observed_mature_pull_requests=min(observed.reviewed_mature_pull_requests, observed.merged_mature_pull_requests),
        replay_replications=len(replications),
        evidence_flags=tuple(flags),
        gates=gates,
        benchmark_label=evidence.delay_benchmark.label,
        benchmark_capacity_queue=evidence.delay_benchmark.capacity_queue,
        benchmark_observations_content_hash=evidence.delay_benchmark.observations_content_hash,
        benchmark_completion_categories=tuple(
            row.completion_categories for row in evidence.delay_benchmark.replications
        ),
        benchmark_comparison=_benchmark_comparison(gates, evidence.delay_benchmark),
        initialization_discrepancy=discrepancy,
        absolute_backlog_forecast_supported=initialization.passed is True,
        unsupported={
            name: Unavailable(None, "unsupported_in_v0_1")
            for name in ("defect_escape_rate", "security_risk_change", "policy_safety")
        },
    )


def _number(value: float | None) -> str:
    return "null" if value is None else f"{value:.6g}"


def _estimate(value: Estimate) -> str:
    return f"{_number(value.value)} [{_number(value.low)}, {_number(value.high)}]; n={value.sample_size}"


def render_validation_report(result: ValidationResult) -> str:
    """Render exact estimates, cohort sizes, variability, and claim limits."""
    evidence_label = (
        f"held-out descriptive {result.status}" if result.protocol == "held_out" else "in-sample diagnostic"
    )
    protocol_warning = (
        "This interval is explicitly an in-sample diagnostic and is not held-out evidence."
        if result.protocol == "in_sample_diagnostic"
        else "The model was frozen before this non-overlapping validation interval."
    )
    gates = "\n".join(
        f"| {gate.metric} | {_estimate(gate.observed)} | {_estimate(gate.simulated)} | "
        f"observed={gate.observed_cohort_size}; "
        f"cohorts={','.join(str(size) for size in gate.simulated_cohort_sizes)} | "
        f"{_number(gate.absolute_error)} | {_number(gate.tolerance)} | "
        f"{'not evaluated' if gate.passed is None else str(gate.passed).lower()} |"
        for gate in result.gates
    )
    flags = ", ".join(result.evidence_flags) if result.evidence_flags else "none"
    backlog = "supported by this descriptive gate" if result.absolute_backlog_forecast_supported else "not supported"
    comparison = "\n".join(
        f"| {row.metric} | {_estimate(row.observed)} | {_estimate(row.mechanistic)} | "
        f"{_estimate(row.elapsed_delay_benchmark)} | {_number(row.mechanistic_absolute_error)} | "
        f"{_number(row.benchmark_absolute_error)} | {row.better_description} |"
        for row in result.benchmark_comparison
    )
    categories = "; ".join(
        f"merged={row.merged}, closed_without_merge={row.closed_without_merge}, not_completed={row.not_completed}"
        for row in result.benchmark_completion_categories
    )
    return (
        "# Historical descriptive validation\n\n"
        f"Status: `{evidence_label}`. Protocol: `{result.protocol}`. {protocol_warning}\n\n"
        f"Model: `{markdown(result.model_version)}`; model content hash: `{result.model_content_hash}`; "
        f"replay arrivals content hash: `{result.replay_arrivals_content_hash}`; dataset content hash: "
        f"`{result.dataset_content_hash}`. "
        f"Training cutoff: `{result.training_cutoff.isoformat()}`. Validation interval: "
        f"`{result.validation_interval_start.isoformat()}` to `{result.validation_interval_end.isoformat()}`.\n\n"
        f"Mature observed cohort: {result.observed_mature_pull_requests}. Replay replications: "
        f"{result.replay_replications}. Evidence flags: {flags}.\n\n"
        "| Metric | Observed estimate [variability]; cohort | Simulated median [5%, 95%]; replications | "
        "Cohort sizes | Absolute error | Tolerance | Gate |\n"
        "| --- | --- | --- | --- | ---: | ---: | --- |\n"
        f"{gates}\n\n"
        "## Elapsed-delay resampling benchmark\n\n"
        "This benchmark is a descriptive reference, not an intervention model. No capacity queue is added; joint "
        "historical review delay and completion-category records are resampled directly onto the same held-out "
        "arrivals and evaluated with the same cohort and horizon definitions.\n\n"
        f"Benchmark observations content hash: `{result.benchmark_observations_content_hash}`. Sampled completion "
        f"categories by replication: {categories}.\n\n"
        "| Metric | Observed | Mechanistic median | Elapsed-delay median | Mechanistic absolute error | "
        "Benchmark absolute error | Lower point-estimate error |\n"
        "| --- | --- | --- | --- | ---: | ---: | --- |\n"
        f"{comparison}\n\n"
        f"Initialization discrepancy: {_estimate(result.initialization_discrepancy)}. "
        f"Absolute backlog forecasting: {backlog}. Warm-up from empty does not guarantee steady state.\n\n"
        "This is historical descriptive validation only. It does not establish causal validation, intervention "
        "validity, or productivity gains and does not establish that auto-approval is safe. `defect_escape_rate`, "
        "`security_risk_change`, "
        "and `policy_safety` are null (reason: `unsupported_in_v0_1`).\n"
    )


def write_validation(result: ValidationResult, out: Path) -> None:
    """Atomically publish the versioned result and deterministic report."""
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError("output directory must be empty or absent")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        payload = result.model_dump_json() + "\n"
        (stage / "validation.json").write_text(payload, encoding="utf-8")
        (stage / "report.md").write_text(render_validation_report(result), encoding="utf-8")
        if out.exists():
            out.rmdir()
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
