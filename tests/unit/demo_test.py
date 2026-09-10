"""The example preset must exercise workload, capacity and revision behavior."""

from datetime import date, datetime, time, timedelta

import pytest

from merge_carlo.demo import demo_experiment
from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI
from merge_carlo.simulation.domain import WorkOrigin

pytestmark = pytest.mark.unit


def test_demo_preset_has_distinct_workloads_and_real_capacity_interventions() -> None:
    config = demo_experiment(17, 3)
    assert (config.root_seed, config.replications) == (17, 3)
    assert config.timezone == "UTC"
    assert [week.week_start for week in config.templates] == [date(2026, 8, 3), date(2026, 8, 10)]
    assert [len(week.arrivals) for week in config.templates] == [15, 20]
    for week in config.templates:
        assert {arrival.offset.days for arrival in week.arrivals} == {0, 1, 2, 3, 4}
        assert {arrival.author_id for arrival in week.arrivals} == {
            "synthetic-author-0",
            "synthetic-author-1",
            "synthetic-author-2",
        }
        assert {arrival.origin for arrival in week.arrivals} == {WorkOrigin.HUMAN}
        assert min(arrival.offset for arrival in week.arrivals) == timedelta(hours=9)
        assert all(
            timedelta(hours=9) <= arrival.offset % timedelta(days=1) < timedelta(hours=10) for arrival in week.arrivals
        )
    assert config.bounds.warmup_seconds == 7 * 86400
    assert config.bounds.observation.seconds == 7 * 86400
    assert config.bounds.observation.start.date() == date(2026, 9, 7)
    assert config.reviewer_calendars == (("synthetic-reviewer", "duty"),)
    duty = dict(config.calendars)["duty"]
    assert duty.timezone == "UTC"
    assert [(w.weekday, w.start, w.end) for w in duty.windows] == [(day, time(9), time(11)) for day in range(5)]
    scenarios = {scenario.name: scenario for scenario in config.scenarios}
    assert scenarios["additive-ai"].demand == AdditiveAI(0.5)
    assert scenarios["replacement-ai"].demand == ReplacementAI(0.5)
    extended = dict(scenarios["extended-duty"].calendars)["duty"]
    assert extended.timezone == "UTC"
    assert [(w.weekday, w.start, w.end) for w in extended.windows] == [(day, time(9), time(13)) for day in range(5)]
    (absence,) = dict(scenarios["reviewer-absence"].absences)["synthetic-reviewer"]
    assert (absence.start, absence.end) == (datetime(2026, 9, 9), datetime(2026, 9, 10))
    bypass = scenarios["hypothetical-bypass"].bypass
    assert bypass is not None
    assert (bypass.eligible_fraction, bypass.audit_fraction) == (0.5, 0.1)
    (base,) = config.assumptions
    assert base.service_seconds == 1800
    assert base.loops.verification_seconds == 300
    assert base.loops.author_response_seconds == 3600
    assert base.loops.verification_failure_probability == 0.05
    assert base.loops.first_change_probability == 0.2
    assert base.loops.repeat_change_probability == 0.1
