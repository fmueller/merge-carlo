"""Measurement-window accounting without event traces or pooled PR summaries."""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from merge_carlo.simulation.domain import PullRequest
from merge_carlo.simulation.domain import PullRequestState as State


@dataclass(frozen=True, slots=True)
class Metric:
    value: float | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MetricWindow:
    start: float
    end: float
    fixed_horizon_seconds: float
    backlog_threshold: int

    def __post_init__(self) -> None:
        if not all(math.isfinite(t) for t in (self.start, self.end, self.fixed_horizon_seconds)):
            raise ValueError("measurement times must be finite")
        if not 0 <= self.start < self.end or self.fixed_horizon_seconds <= 0:
            raise ValueError("measurement window and fixed horizon must be positive")
        if type(self.backlog_threshold) is not int or self.backlog_threshold < 0:
            raise ValueError("backlog threshold must be a nonnegative integer")


@dataclass(frozen=True, slots=True)
class HorizonShare:
    total: int
    eligible: int
    excluded: int
    share: Metric


@dataclass(frozen=True, slots=True)
class MetricDictionary:
    arrivals: int
    merges: int
    abandonments: int
    wip_start: int
    wip_end: int
    queue_peak: int
    queue_time_average: float
    backlog_exceeded: int
    first_review_median: Metric
    first_review_p95: Metric
    ready_to_merge_median: Metric
    ready_to_merge_p95: Metric
    queue_wait_seconds: float
    reviewed: HorizonShare
    merged: HorizonShare
    unresolved_share: Metric
    review_utilization: Metric
    requested_changes: int
    unreviewed_merges: int


@dataclass(frozen=True, slots=True)
class RunMetrics:
    all_work: MetricDictionary
    new_ready: MetricDictionary


@dataclass(frozen=True, slots=True)
class MetricSummary:
    total: int
    defined: int
    excluded: int
    median: Metric
    low: Metric
    high: Metric


def _quantile(values: list[float], q: float, reason: str) -> Metric:
    return Metric(float(np.quantile(values, q))) if values else Metric(None, reason)


def summarize_metrics(metrics: Iterable[Metric]) -> MetricSummary:
    """Median and central 90% of run-level values, using linear quantiles.

    Consumers select a field from persisted replication rows, separately for
    each assumption/scenario/level. Undefined runs are counted, never imputed.
    """
    rows = tuple(metrics)
    values = [m.value for m in rows if m.value is not None]
    return MetricSummary(
        len(rows),
        len(values),
        len(rows) - len(values),
        *(_quantile(values, q, "no_defined_replications") for q in (0.5, 0.05, 0.95)),
    )


class Measurement:
    """Internal engine accumulator: interval integrals and first completions."""

    def __init__(self, window: MetricWindow) -> None:
        self.window = window
        self.queue_area = [0.0, 0.0]
        self.queue_peak = [0, 0]
        self.service = [0.0, 0.0]
        self.changes = [0, 0]
        self.first_completed: dict[str, float] = {}

    def advance(self, states: Mapping[str, PullRequest], previous: float, now: float, active: set[str]) -> None:
        duration = max(0.0, min(now, self.window.end) - max(previous, self.window.start))
        if not duration:
            return
        for level in (0, 1):
            selected = [p for p in states.values() if level == 0 or p.ready_at >= self.window.start]
            queued = sum(p.state is State.QUEUED_FOR_REVIEW for p in selected)
            self.queue_area[level] += queued * duration
            self.queue_peak[level] = max(self.queue_peak[level], queued)
            self.service[level] += sum(p.pr_id in active for p in selected) * duration

    def completed_review(self, p: PullRequest, at: float, requested_changes: bool) -> None:
        self.first_completed.setdefault(p.pr_id, at)
        if self.window.start <= at < self.window.end and requested_changes:
            self.changes[0] += 1
            if p.ready_at >= self.window.start:
                self.changes[1] += 1

    def finish(self, proposals: tuple[PullRequest, ...], duty_seconds: float) -> RunMetrics:
        window = self.window

        def dictionary(level: int) -> MetricDictionary:
            # Operational population: carry-in plus new arrivals, excluding
            # work resolved before measurement. Censoring is not resolution.
            selected = [
                p
                for p in proposals
                if p.ready_at < window.end
                and (level == 0 or p.ready_at >= window.start)
                and (p.terminal_at is None or p.censored or p.terminal_at >= window.start)
            ]
            merged = [
                p
                for p in selected
                if p.state is State.MERGED and p.terminal_at is not None and window.start <= p.terminal_at < window.end
            ]
            abandoned = sum(
                p.state is State.CLOSED_WITHOUT_MERGE
                and p.terminal_at is not None
                and window.start <= p.terminal_at < window.end
                for p in selected
            )
            arrivals = sum(p.ready_at >= window.start for p in selected)
            carry = sum(p.ready_at < window.start for p in selected)
            unresolved = len(selected) - len(merged) - abandoned
            review_delays = [
                p.first_review_at - p.ready_at
                for p in selected
                if p.first_review_at is not None
                and p.pr_id in self.first_completed
                and window.start <= self.first_completed[p.pr_id] < window.end
            ]
            merge_delays = [p.terminal_at - p.ready_at for p in merged if p.terminal_at is not None]

            def share(review: bool) -> HorizonShare:
                # A deadline exactly at the half-open end is not observable.
                eligible = [p for p in selected if p.ready_at + window.fixed_horizon_seconds < window.end]
                successes = 0
                for p in eligible:
                    at = (
                        self.first_completed.get(p.pr_id)
                        if review
                        else (p.terminal_at if p.state is State.MERGED else None)
                    )
                    successes += at is not None and at <= p.ready_at + window.fixed_horizon_seconds
                return HorizonShare(
                    len(selected),
                    len(eligible),
                    len(selected) - len(eligible),
                    Metric(successes / len(eligible)) if eligible else Metric(None, "no_eligible_cohort"),
                )

            return MetricDictionary(
                arrivals,
                len(merged),
                abandoned,
                carry,
                unresolved,
                self.queue_peak[level],
                self.queue_area[level] / (window.end - window.start),
                int(self.queue_peak[level] > window.backlog_threshold),
                _quantile(review_delays, 0.5, "no_completed_reviews"),
                _quantile(review_delays, 0.95, "no_completed_reviews"),
                _quantile(merge_delays, 0.5, "no_merges"),
                _quantile(merge_delays, 0.95, "no_merges"),
                self.queue_area[level],
                share(True),
                share(False),
                Metric(unresolved / len(selected)) if selected else Metric(None, "no_eligible_cohort"),
                Metric(self.service[level] / duty_seconds)
                if duty_seconds
                else Metric(None, "no_declared_review_capacity"),
                self.changes[level],
                sum(p.first_review_at is None for p in merged),
            )

        return RunMetrics(dictionary(0), dictionary(1))
