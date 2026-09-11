"""Versioned aggregate contracts and deterministic, artifact-only reporting."""

import math
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from merge_carlo.simulation.metrics import Metric, MetricSummary

_MAX_SUMMARY_BYTES = 16 * 1024 * 1024


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1


class Evidence(Contract):
    """Caller-declared evidence, never a claim of fitted or validated behavior."""

    synthetic: bool
    training_cutoff: str | None
    template_basis: Literal["observed", "derived", "proxy", "assumed"] = "assumed"
    validation_status: Literal["not_performed", "pass", "fail", "insufficient_evidence"] = "not_performed"


class Probability(Contract):
    successes: int = Field(ge=0, strict=True)
    trials: int = Field(ge=0, strict=True)
    estimate: Metric
    low: float | None
    high: float | None

    @model_validator(mode="after")
    def check_probability(self) -> Self:
        if self.successes > self.trials:
            raise ValueError("successes exceed trials")
        if not self.trials:
            if (
                self.estimate != Metric(None, "no_defined_replications")
                or self.low is not None
                or self.high is not None
            ):
                raise ValueError("zero trials require undefined probability and bounds")
        elif (
            self.estimate.value is None
            or not math.isclose(self.estimate.value, self.successes / self.trials)
            or self.estimate.reason is not None
            or self.low is None
            or self.high is None
            or not 0 <= self.low <= self.estimate.value <= self.high <= 1
        ):
            raise ValueError("invalid probability estimate or bounds")
        return self


def wilson(successes: int, trials: int) -> Probability:
    """Two-sided 95% Wilson interval, including zero-event finite samples."""
    if not 0 <= successes <= trials:
        raise ValueError("successes must be between zero and trials")
    if not trials:
        return Probability(successes=0, trials=0, estimate=Metric(None, "no_defined_replications"), low=None, high=None)
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    radius = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return Probability(
        successes=successes,
        trials=trials,
        estimate=Metric(p),
        low=0.0 if successes == 0 else center - radius,
        high=1.0 if successes == trials else center + radius,
    )


class SummaryRow(Contract):
    assumption: str
    scenario: str
    metric: str
    summary: MetricSummary
    event_probability: Probability | None = None


class Comparison(Contract):
    assumption: str
    scenario: str
    absolute: MetricSummary
    relative: MetricSummary
    more_merges: Probability


class ReplicationCount(Contract):
    """Runs per assumption/scenario; an engine-truncated run contributes no outcome values."""

    assumption: str
    scenario: str
    requested: int = Field(gt=0, strict=True)
    usable: int = Field(ge=0, strict=True)
    engine_truncated: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def check_total(self) -> Self:
        if self.usable + self.engine_truncated != self.requested:
            raise ValueError("usable and engine-truncated counts must sum to requested")
        return self


class Summary(Contract):
    evidence: Evidence
    requested_replications: int = Field(gt=0, strict=True)
    comparison_incomplete: bool
    limitations: list[str]
    replication_counts: list[ReplicationCount]
    rows: list[SummaryRow]
    comparisons: list[Comparison]

    @model_validator(mode="after")
    def check_replication_counts(self) -> Self:
        usable: dict[tuple[str, str], int] = {}
        for count in self.replication_counts:
            key = (count.assumption, count.scenario)
            if key in usable:
                raise ValueError("duplicate replication counts")
            if count.requested != self.requested_replications:
                raise ValueError("replication counts must match requested replications")
            usable[key] = count.usable
        if any(count.engine_truncated for count in self.replication_counts) and not self.comparison_incomplete:
            raise ValueError("engine truncation requires an incomplete comparison")
        defined = [((row.assumption, row.scenario), row.summary.defined) for row in self.rows]
        defined.extend(
            ((pair.assumption, side), stats.defined)
            for pair in self.comparisons
            for side in (pair.scenario, "baseline")
            for stats in (pair.absolute, pair.relative)
        )
        for key, outcomes in defined:
            if key not in usable:
                raise ValueError("missing replication counts")
            if outcomes > usable[key]:
                raise ValueError("defined outcomes exceed usable replications")
        return self

    @model_validator(mode="after")
    def check_summaries(self) -> Self:
        for row in self.rows:
            if row.event_probability is not None and row.event_probability.trials != row.summary.defined:
                raise ValueError("event probability trials must equal defined replications")
        for pair in self.comparisons:
            if pair.more_merges.trials != pair.absolute.defined:
                raise ValueError("paired probability trials must equal defined pairs")
        summaries = [row.summary for row in self.rows]
        summaries.extend(stats for pair in self.comparisons for stats in (pair.absolute, pair.relative))
        for stats in summaries:
            if (
                stats.total != self.requested_replications
                or min(stats.defined, stats.excluded) < 0
                or stats.defined + stats.excluded != stats.total
            ):
                raise ValueError("inconsistent replication counts")
            metrics = (stats.low, stats.median, stats.high)
            if not stats.defined:
                if any(metric != Metric(None, "no_defined_replications") for metric in metrics):
                    raise ValueError("undefined summary requires null values and reasons")
            else:
                values = [metric.value for metric in metrics if metric.value is not None]
                if (
                    len(values) != 3
                    or not all(math.isfinite(value) for value in values)
                    or values != sorted(values)
                    or any(metric.reason is not None for metric in metrics)
                ):
                    raise ValueError("invalid summary quantiles")
        return self


def markdown(value: str) -> str:
    """Escape metadata as literal text, including HTML, pipes and newlines."""
    return "".join(
        f"&#{ord(c)};" if c in "\\`*_{}[]<>()#+-.!|&\"'" or ord(c) < 32 or ord(c) == 127 else c for c in value
    )


def _number(value: float | None) -> str:
    return "null" if value is None else f"{value:.6g}"


def _range(summary: MetricSummary) -> str:
    return (
        f"{_number(summary.median.value)} [{_number(summary.low.value)}, {_number(summary.high.value)}]"
        f"; {summary.defined}/{summary.total} defined"
    )


def _probability(probability: Probability) -> str:
    return (
        f"{probability.successes}/{probability.trials}; {_number(probability.estimate.value)} "
        f"[95% Wilson: {_number(probability.low)}, {_number(probability.high)}]"
    )


def _replication_counts(summary: Summary) -> str:
    truncated = sum(count.engine_truncated for count in summary.replication_counts)
    runs = sum(count.requested for count in summary.replication_counts)
    ranking = (
        f"Policy ranking disabled: {truncated} of {runs} runs engine-truncated, "
        "which marks the whole comparison incomplete."
        if truncated
        else "No policy ranking is produced."
    )
    return (
        f"{ranking}\n\n"
        "Replication counts per assumption/scenario. An engine-truncated run contributes no outcome values, "
        "including merges before truncation; zero usable runs leave outcomes undefined, never zero.\n\n"
        "| Assumption | Scenario | Requested | Usable | Engine-truncated |\n"
        "| --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {markdown(count.assumption)} | {markdown(count.scenario)} | "
            f"{count.requested} | {count.usable} | {count.engine_truncated} |"
            for count in summary.replication_counts
        )
    )


def render_report(results: Path) -> str:
    """Read only summary.json. Never import a runner, fetch data or simulate."""
    with (results / "summary.json").open("rb") as source:
        payload = source.read(_MAX_SUMMARY_BYTES + 1)
    if len(payload) > _MAX_SUMMARY_BYTES:
        raise ValueError("summary exceeds 16 MiB")
    summary = Summary.model_validate_json(payload)
    label = "SYNTHETIC" if summary.evidence.synthetic else "CONDITIONAL MODEL OUTPUT"
    sections = [
        f"# Experiment report — {label}",
        f"## Question and evidence status — {label}\n\n"
        "How do declared workload and review-capacity scenarios change conditional review-system outcomes?\n\n"
        f"Validation: {summary.evidence.validation_status}. "
        f"Requested replications per assumption/scenario: {summary.requested_replications}. "
        f"Comparison incomplete: {str(summary.comparison_incomplete).lower()}. {_replication_counts(summary)}",
        f"## Scenario comparison — {label}\n\n"
        "Load-response metrics: run-level median [central 90% range], not pooled PR observations. "
        "Undefined runs are excluded explicitly; null is not zero.\n\n"
        "| Assumption | Scenario | Population.metric | Median [5%, 95%]; defined/requested |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {markdown(row.assumption)} | {markdown(row.scenario)} | "
            f"{markdown(row.metric)} | {_range(row.summary)} |"
            for row in summary.rows
        ),
        f"## Uncertainty and robustness — {label}\n\n"
        "Monte Carlo estimation error is separate from run-to-run variation and assumption uncertainty. "
        "Named assumption sets are not a probability distribution. All probabilities below are conditional "
        "on the model and the named assumption set. More merges is a direction, not a policy recommendation.\n\n"
        "| Assumption | Scenario | Paired merge delta | Relative delta | Runs with more merges |\n"
        "| --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {markdown(row.assumption)} | {markdown(row.scenario)} | {_range(row.absolute)} | "
            f"{_range(row.relative)} | {_probability(row.more_merges)} |"
            for row in summary.comparisons
        )
        + "\n\nBacklog threshold exceedance (strictly above the declared threshold):\n\n"
        + "\n".join(
            f"- {markdown(row.assumption)} / {markdown(row.scenario)} / {markdown(row.metric)}: "
            f"{_probability(row.event_probability)}"
            for row in summary.rows
            if row.event_probability is not None
        ),
        f"## Assumptions and data coverage — {label}\n\n"
        f"Training cutoff: {markdown(summary.evidence.training_cutoff or 'not supplied')}. "
        "See model-card.json for provenance and resolved-scenarios.json for exact parameters, calendars, "
        "local timezone and UTC bounds. Effort is assumed active service, never observed elapsed delay.\n\n"
        + "\n".join(f"- {markdown(limit)}" for limit in summary.limitations),
        f"## Interpretation — {label}\n\n"
        "The model covers CI-before-review, one-required-review, a central FIFO queue and declared duty. "
        "It does not emulate branch protection. Latencies are completion-conditioned; read them alongside "
        "unresolved work and fixed-horizon shares. Warm-up from empty does not guarantee steady state. "
        "Truncated runs are excluded, never converted to favorable zero outcomes. "
        "Assumption-sensitive differences call for measuring active effort and availability, not selecting a winner. "
        "Historical fit is not causal validation. Removing review also removes modeled requested changes; "
        "flow differences are not net engineering benefit. No real GitHub action is taken.\n\n"
        "defect_escape_rate: null; security_risk_change: null; policy_safety: null "
        "(reason for each: unsupported_in_v0_1).",
        f"## Reproduction — {label}\n\n"
        "manifest.json records versions, SHA-256 content hashes, seed, RNG scheme and evidence status. "
        "replications.jsonl and paired-deltas.jsonl preserve run-level values and undefined reasons. "
        "traces.jsonl contains only requested sampled engine diagnostics, not a full transition log. "
        "Re-render with merge_carlo.reporting.render_report(Path(results_directory)); this only reads artifacts. "
        "Reconstruct an Experiment manually from resolved-scenarios.json, including demand_kinds, "
        "then call merge_carlo.artifacts.write_experiment; there is no automatic replay loader. "
        "Reproducibility is limited to the locked reference environment, not arbitrary library versions or hardware. "
        "Metadata may remain identifiable; share only authorized data.",
    ]
    if {row.assumption for row in summary.rows} == {"base"}:
        sections = [
            section + "\n\nOnly the base assumption set was run. Full sensitivity has not been run."
            for section in sections
        ]
    return "\n\n".join(sections) + "\n"
