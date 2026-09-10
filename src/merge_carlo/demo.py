"""Small synthetic inputs for an offline demonstration, never measured team data."""

from datetime import date, datetime, time, timedelta

from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI, TemplateArrival, WeekTemplate
from merge_carlo.simulation.calendars import DutyCalendar, LocalAbsence, WeeklyWindow, materialize_run_bounds
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.simulation.engine import ReviewBypass, RevisionLoops
from merge_carlo.simulation.runner import AssumptionSet, Experiment, Scenario


def demo_experiment(seed: int, replications: int) -> Experiment:
    """Keep all example inputs in the versioned resolved experiment artifact."""
    duty = DutyCalendar("UTC", tuple(WeeklyWindow(f"day-{day}", day, time(9), time(11)) for day in range(5)))
    extended = DutyCalendar("UTC", tuple(WeeklyWindow(f"day-{day}", day, time(9), time(13)) for day in range(5)))
    return Experiment(
        templates=tuple(
            WeekTemplate(
                date(2026, 8, 3) + timedelta(weeks=week),
                tuple(
                    TemplateArrival(
                        timedelta(days=day, hours=9, minutes=15 * arrival),
                        f"synthetic-author-{arrival % 3}",
                        WorkOrigin.HUMAN,
                    )
                    for day in range(5)
                    for arrival in range(3 + week)
                ),
            )
            for week in range(2)
        ),
        timezone="UTC",
        bounds=materialize_run_bounds(datetime(2026, 9, 7), "UTC", horizon_days=7, warmup_days=7),
        calendars=(("duty", duty),),
        reviewer_calendars=(("synthetic-reviewer", "duty"),),
        assumptions=(
            AssumptionSet(
                "base",
                1800,
                RevisionLoops(
                    verification_seconds=300,
                    author_response_seconds=3600,
                    verification_failure_probability=0.05,
                    first_change_probability=0.2,
                    repeat_change_probability=0.1,
                ),
            ),
        ),
        scenarios=(
            Scenario("additive-ai", demand=AdditiveAI(0.5)),
            Scenario("replacement-ai", demand=ReplacementAI(0.5)),
            Scenario("extended-duty", calendars=(("duty", extended),)),
            Scenario(
                "reviewer-absence",
                absences=(("synthetic-reviewer", (LocalAbsence(datetime(2026, 9, 9), datetime(2026, 9, 10)),)),),
            ),
            Scenario("hypothetical-bypass", bypass=ReviewBypass(0.5, 0.1)),
        ),
        root_seed=seed,
        replications=replications,
        backlog_threshold=5,
    )
