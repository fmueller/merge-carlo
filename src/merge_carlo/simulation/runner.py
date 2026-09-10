"""Sequential paired runs; memory is bounded by one pair, not replication count.

These Python contracts carry assumed parameters. Artifact schemas are a separate
layer. No scenario or assumption name enters a
random key: shared proposals map common latent draws through their parameters.
"""

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI, WeekTemplate, generate_proposals
from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, RunBounds, UTCInterval
from merge_carlo.simulation.capacity import materialize_reviewers
from merge_carlo.simulation.engine import Abandonment, FIFOResult, ReviewBypass, RevisionLoops, run_fifo
from merge_carlo.simulation.metrics import MetricWindow, RunMetrics


@dataclass(frozen=True, slots=True)
class AssumptionSet:
    """Named assumed service and behavior, never observed elapsed review effort."""

    name: str
    service_seconds: float
    loops: RevisionLoops = RevisionLoops()
    abandonment: Abandonment | None = None
    coordination_seconds: float = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.service_seconds, bool)
            or not math.isfinite(self.service_seconds)
            or self.service_seconds < 1
        ):
            raise ValueError("constant service must be finite and at least one second")
        if (
            isinstance(self.coordination_seconds, bool)
            or not math.isfinite(self.coordination_seconds)
            or self.coordination_seconds < 0
        ):
            raise ValueError("coordination delay must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class Scenario:
    """Closed intervention fields; baseline is implicit and cannot be overridden."""

    name: str
    demand: AdditiveAI | ReplacementAI | None = None
    calendars: tuple[tuple[str, DutyCalendar], ...] = ()
    absences: tuple[tuple[str, tuple[LocalAbsence, ...]], ...] = ()
    bypass: ReviewBypass | None = None


def _unique(names: tuple[str, ...]) -> None:
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("names must be nonempty and unique")


@dataclass(frozen=True, slots=True)
class Experiment:
    templates: tuple[WeekTemplate, ...]
    timezone: str
    bounds: RunBounds
    calendars: tuple[tuple[str, DutyCalendar], ...]
    reviewer_calendars: tuple[tuple[str, str], ...]
    assumptions: tuple[AssumptionSet, ...]
    scenarios: tuple[Scenario, ...]
    root_seed: int
    replications: int
    trace_replications: tuple[int, ...] = ()
    fixed_horizon_seconds: float = 86400
    backlog_threshold: int = 0

    def __post_init__(self) -> None:
        MetricWindow(0, self.bounds.observation.seconds, self.fixed_horizon_seconds, self.backlog_threshold)
        if type(self.root_seed) is not int or self.root_seed < 0:
            raise ValueError("root seed must be a nonnegative integer")
        if type(self.replications) is not int or self.replications < 1:
            raise ValueError("replications must be a positive integer")
        if not self.assumptions:
            raise ValueError("at least one assumption set is required")
        if self.bounds.warmup_start.utcoffset() != self.bounds.observation.start.utcoffset():
            raise ValueError("warm-up start must be UTC")
        if self.bounds.warmup_seconds < 0:
            raise ValueError("warm-up must precede measurement")
        _unique(tuple(a.name for a in self.assumptions))
        _unique(("baseline", *(s.name for s in self.scenarios)))
        for entries in (self.calendars, self.reviewer_calendars):
            _unique(tuple(name for name, _ in entries))
        for scenario in self.scenarios:
            _unique(tuple(name for name, _ in scenario.calendars))
            _unique(tuple(name for name, _ in scenario.absences))
        if any(type(n) is not int or not 0 <= n < self.replications for n in self.trace_replications):
            raise ValueError("trace replication indexes must be within the experiment")


@dataclass(frozen=True, slots=True)
class RunCounts:
    """Measurement-window merge count; a truncated run has no usable outcome."""

    merges: int | None
    engine_truncated: bool
    metrics: RunMetrics | None = None


@dataclass(frozen=True, slots=True)
class CountSummary:
    """Streaming count diagnostic, not a pooled latency distribution or ranking."""

    valid_replications: int = 0
    engine_truncated_count: int = 0
    merges: int | None = None


@dataclass(frozen=True, slots=True)
class PairedRow:
    assumption_id: str
    replication: int
    scenario_id: str
    baseline: RunCounts
    scenario: RunCounts
    merge_delta: int | None
    limitations: tuple[str, ...]
    trace: tuple[FIFOResult, FIFOResult] | None


class ExperimentRun(Iterator[PairedRow]):
    """One-shot stream. Summaries describe only consumed rows, keyed by assumption.

    Consume to exhaustion before interpreting completeness. A baseline-only
    experiment emits a baseline self-pair. Consumers may persist rows immediately;
    retaining them (especially sampled diagnostics) is the consumer's choice.
    """

    def __init__(self, experiment: Experiment) -> None:
        self._summaries: dict[tuple[str, str], CountSummary] = {}
        self._exhausted = False
        self._rows = self._iterate(experiment)

    @property
    def summaries(self) -> Mapping[tuple[str, str], CountSummary]:
        return MappingProxyType(self._summaries)

    @property
    def comparison_incomplete(self) -> bool:
        return not self._exhausted or any(s.engine_truncated_count for s in self._summaries.values())

    def __next__(self) -> PairedRow:
        return next(self._rows)

    def _record(self, key: tuple[str, str], counts: RunCounts) -> None:
        old = self._summaries.get(key, CountSummary())
        self._summaries[key] = CountSummary(
            old.valid_replications + (not counts.engine_truncated),
            old.engine_truncated_count + counts.engine_truncated,
            old.merges if counts.merges is None else (old.merges or 0) + counts.merges,
        )

    def _iterate(self, experiment: Experiment) -> Iterator[PairedRow]:
        span = UTCInterval(experiment.bounds.warmup_start, experiment.bounds.observation.end)
        scenarios = sorted(experiment.scenarios, key=lambda s: s.name)
        baseline = Scenario("baseline")

        def simulate(
            scenario: Scenario, assumption: AssumptionSet, replication: int
        ) -> tuple[FIFOResult, RunCounts, tuple[str, ...]]:
            schedule = generate_proposals(
                experiment.templates,
                span=span,
                timezone=experiment.timezone,
                root_seed=experiment.root_seed,
                replication=replication,
                scenario=scenario.demand,
            )
            reviewers = materialize_reviewers(
                dict(experiment.calendars),
                dict(experiment.reviewer_calendars),
                span=span,
                overrides=dict(scenario.calendars),
                absences=dict(scenario.absences),
            )
            result = run_fifo(
                schedule.proposals,
                reviewers,
                span=span,
                service_seconds=assumption.service_seconds,
                loops=assumption.loops,
                abandonment=assumption.abandonment,
                bypass=scenario.bypass,
                coordination_seconds=assumption.coordination_seconds,
                root_seed=experiment.root_seed,
                replication=replication,
                measurement=MetricWindow(
                    experiment.bounds.warmup_seconds,
                    span.seconds,
                    experiment.fixed_horizon_seconds,
                    experiment.backlog_threshold,
                ),
            )
            counts = RunCounts(
                result.metrics.all_work.merges if result.metrics is not None else None,
                result.engine_truncated,
                result.metrics,
            )
            return result, counts, schedule.limitations + result.limitations

        for assumption in sorted(experiment.assumptions, key=lambda a: a.name):
            for replication in range(experiment.replications):
                baseline_result, baseline_counts, baseline_limits = simulate(baseline, assumption, replication)
                self._record((assumption.name, "baseline"), baseline_counts)
                for scenario in scenarios or [baseline]:
                    if scenario is baseline:
                        result, counts, limits = baseline_result, baseline_counts, baseline_limits
                    else:
                        result, counts, limits = simulate(scenario, assumption, replication)
                        self._record((assumption.name, scenario.name), counts)
                    yield PairedRow(
                        assumption.name,
                        replication,
                        scenario.name,
                        baseline_counts,
                        counts,
                        None
                        if baseline_counts.merges is None or counts.merges is None
                        else counts.merges - baseline_counts.merges,
                        tuple(sorted(set(baseline_limits + limits))),
                        (baseline_result, result) if replication in experiment.trace_replications else None,
                    )
        self._exhausted = True


def run_experiment(experiment: Experiment) -> ExperimentRun:
    """Create a lazy stream; no file IO, network, global generator or workers."""
    return ExperimentRun(experiment)
