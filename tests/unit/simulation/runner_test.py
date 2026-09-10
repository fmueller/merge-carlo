"""Paired execution uses real arrivals and FIFO state, not mocked outcomes."""

import gc
import tracemalloc
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, time, timedelta

import pytest

from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI, TemplateArrival, WeekTemplate
from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, WeeklyWindow, materialize_run_bounds
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.simulation.engine import Abandonment, ReviewBypass, RevisionLoops
from merge_carlo.simulation.runner import AssumptionSet, Experiment, Scenario, run_experiment

pytestmark = pytest.mark.unit


def experiment(replications: int = 2) -> Experiment:
    return Experiment(
        templates=(
            WeekTemplate(
                date(2026, 9, 7),
                (
                    TemplateArrival(timedelta(hours=23, minutes=59, seconds=50), "a", WorkOrigin.HUMAN),
                    TemplateArrival(timedelta(days=1, seconds=5), "a", WorkOrigin.HUMAN),
                ),
            ),
        ),
        timezone="UTC",
        bounds=materialize_run_bounds(datetime(2026, 9, 8), "UTC", horizon_days=1, warmup_days=1),
        calendars=(
            (
                "duty",
                DutyCalendar(
                    "UTC",
                    (
                        WeeklyWindow("mon", 0, time(0), time(0, 0, 1)),
                        WeeklyWindow("tue", 1, time(0), time(1)),
                    ),
                ),
            ),
        ),
        reviewer_calendars=(("r", "duty"),),
        assumptions=(AssumptionSet("fast", 10), AssumptionSet("slow", 10000)),
        scenarios=(Scenario("bypass", bypass=ReviewBypass(1, 0)), Scenario("load", demand=AdditiveAI(1))),
        root_seed=42,
        replications=replications,
    )


def test_pairs_warmup_and_separate_assumption_summaries() -> None:
    runner = run_experiment(experiment())
    rows = list(runner)
    assert len(rows) == 8
    assert {(r.assumption_id, r.replication, r.scenario_id) for r in rows} == {
        (a, n, s) for a in ("fast", "slow") for n in range(2) for s in ("bypass", "load")
    }
    fast = next(r for r in rows if r.assumption_id == "fast" and r.scenario_id == "bypass")
    assert fast.baseline.merges == 2  # includes carry-in, not a restart at measurement
    assert fast.scenario.merges == 1  # warm-up bypass merge is excluded
    assert fast.merge_delta == -1
    assert fast.trace is None
    assert fast.baseline.metrics is not None
    assert fast.baseline.metrics.all_work.merges == 2
    assert fast.baseline.metrics.new_ready.merges == 1
    assert "exploratory_only" in fast.limitations
    slow = next(r for r in rows if r.assumption_id == "slow" and r.scenario_id == "bypass")
    assert slow.baseline.merges == 0
    assert slow.merge_delta == 1
    assert runner.summaries[("fast", "baseline")].merges == 4
    assert runner.summaries[("slow", "baseline")].merges == 0


def test_reproducibility_and_scenario_order_independence() -> None:
    config = experiment()
    original = list(run_experiment(config))
    assert original == list(run_experiment(config))
    changed = replace(config, scenarios=(Scenario("extra"), *reversed(config.scenarios)))
    assert original == [r for r in run_experiment(changed) if r.scenario_id != "extra"]


def test_partial_stream_is_incomplete_and_baseline_only_runs_once() -> None:
    runner = run_experiment(replace(experiment(), scenarios=()))
    assert runner.comparison_incomplete
    first = next(runner)
    assert first.scenario_id == "baseline"
    assert first.scenario == first.baseline
    assert first.merge_delta == 0
    assert runner.comparison_incomplete
    assert len(list(runner)) == 3
    assert not runner.comparison_incomplete
    assert runner.summaries[("fast", "baseline")].valid_replications == 2
    assert list(runner) == []


def test_measurement_includes_start_but_excludes_end() -> None:
    config = replace(
        experiment(1),
        templates=(
            WeekTemplate(
                date(2026, 9, 7),
                (
                    TemplateArrival(timedelta(days=1), "a", WorkOrigin.HUMAN),
                    TemplateArrival(timedelta(days=1, seconds=5), "a", WorkOrigin.HUMAN),
                ),
            ),
        ),
        assumptions=(AssumptionSet("instant", 10), AssumptionSet("horizon", 10, coordination_seconds=86400)),
        scenarios=(Scenario("bypass", bypass=ReviewBypass(1, 0)),),
    )
    rows = {r.assumption_id: r for r in run_experiment(config)}
    assert rows["instant"].scenario.merges == 2
    assert rows["horizon"].scenario.merges == 0


def test_truncated_baseline_excludes_pair_but_keeps_valid_scenario() -> None:
    config = replace(
        experiment(),
        assumptions=(AssumptionSet("loop", 10, loops=RevisionLoops(first_change_probability=1, max_review_visits=1)),),
    )
    runner = run_experiment(config)
    rows = list(runner)
    bypass = next(r for r in rows if r.scenario_id == "bypass")
    assert bypass.baseline.merges is None
    assert bypass.baseline.engine_truncated
    assert bypass.baseline.metrics is None
    assert bypass.scenario.merges == 1
    assert bypass.merge_delta is None
    assert runner.comparison_incomplete
    assert runner.summaries[("loop", "baseline")].merges is None
    assert runner.summaries[("loop", "baseline")].engine_truncated_count == 2
    assert runner.summaries[("loop", "bypass")].valid_replications == 2


def test_capacity_replacement_and_sampled_diagnostics_preserve_baseline() -> None:
    config = replace(
        experiment(),
        trace_replications=(1,),
        scenarios=(
            Scenario("absent", absences=(("r", (LocalAbsence(datetime(2026, 9, 8), datetime(2026, 9, 9)),)),)),
            Scenario("closed", calendars=(("duty", DutyCalendar("UTC", ())),)),
            Scenario("replacement", demand=ReplacementAI(1)),
        ),
    )
    before = repr(config)
    rows = list(run_experiment(config))
    assert repr(config) == before
    for row in rows:
        assert (row.trace is not None) == (row.replication == 1)
        if row.trace is not None:
            baseline, scenario = row.trace
            assert all(p.origin is WorkOrigin.HUMAN for p in baseline.pull_requests)
            if row.scenario_id == "replacement":
                assert all(p.origin is WorkOrigin.AI for p in scenario.pull_requests)
                assert [(p.pr_id, p.ready_at) for p in baseline.pull_requests] == [
                    (p.pr_id, p.ready_at) for p in scenario.pull_requests
                ]
            else:
                assert row.scenario.merges == 0
                assert any("no_eligible_reviewer" in limit for limit in row.limitations)
    with pytest.raises(FrozenInstanceError):
        config.assumptions[0].service_seconds = 1  # type: ignore[misc]


def test_stochastic_forwarding_replays_engine_with_same_keys() -> None:
    from merge_carlo.simulation.arrivals import generate_proposals
    from merge_carlo.simulation.calendars import UTCInterval
    from merge_carlo.simulation.capacity import materialize_reviewers
    from merge_carlo.simulation.engine import run_fifo
    from merge_carlo.simulation.metrics import MetricWindow

    assumption = AssumptionSet("random", 17, RevisionLoops(3, 11, 0.2, 0.6, 0.3), Abandonment(0.4, (8, 90)), 7)
    config = replace(experiment(6), assumptions=(assumption,), trace_replications=tuple(range(6)))
    span = UTCInterval(config.bounds.warmup_start, config.bounds.observation.end)
    for row in run_experiment(config):
        assert row.trace is not None
        proposals = generate_proposals(
            config.templates, span=span, timezone=config.timezone, root_seed=42, replication=row.replication
        )
        expected = run_fifo(
            proposals.proposals,
            materialize_reviewers(dict(config.calendars), dict(config.reviewer_calendars), span=span),
            span=span,
            service_seconds=17,
            loops=assumption.loops,
            abandonment=assumption.abandonment,
            coordination_seconds=7,
            root_seed=42,
            replication=row.replication,
            measurement=MetricWindow(config.bounds.warmup_seconds, span.seconds, 86400, 0),
        )
        assert row.trace[0] == expected


def test_stream_memory_is_bounded_by_pair_not_replication_count() -> None:
    def peak(count: int) -> int:
        gc.collect()
        tracemalloc.start()
        maximum = 0
        for index, row in enumerate(run_experiment(experiment(count))):
            assert row.trace is None
            if index % 20 == 0:
                # Measure live state, not Python's delayed garbage collection
                # or freelists, which depend on unrelated earlier tests.
                gc.collect()
                current, _ = tracemalloc.get_traced_memory()
                maximum = max(maximum, current)
        tracemalloc.stop()
        return maximum

    peak(1)  # warm imports/caches before measuring
    small = peak(4)
    large = peak(100)
    assert large < small + 80_000


@pytest.mark.parametrize(
    "field,value",
    [
        ("replications", 0),
        ("replications", -1),
        ("replications", True),
        ("root_seed", -1),
        ("root_seed", True),
        ("assumptions", ()),
        ("assumptions", (AssumptionSet("a", 1), AssumptionSet("a", 2))),
        ("scenarios", (Scenario("baseline"),)),
        ("scenarios", (Scenario(""),)),
        ("trace_replications", (-1,)),
        ("trace_replications", (2,)),
        ("trace_replications", (True,)),
        ("calendars", (("x", DutyCalendar("UTC", ())), ("x", DutyCalendar("UTC", ())))),
        ("reviewer_calendars", (("r", "duty"), ("r", "duty"))),
        ("scenarios", (Scenario("x", calendars=(("d", DutyCalendar("UTC", ())), ("d", DutyCalendar("UTC", ())))),)),
        ("scenarios", (Scenario("x", absences=(("r", ()), ("r", ()))),)),
    ],
)
def test_invalid_experiment(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        replace(experiment(), **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf"), True, False])
def test_invalid_service(duration: float) -> None:
    with pytest.raises(ValueError):
        AssumptionSet("bad", duration)


@pytest.mark.parametrize("delay", [-1, float("nan"), float("inf"), True, False])
def test_invalid_coordination(delay: float) -> None:
    with pytest.raises(ValueError):
        AssumptionSet("bad", 1, coordination_seconds=delay)
