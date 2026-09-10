from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.arrivals import TemplateArrival, WeekTemplate, generate_proposals
from merge_carlo.simulation.calendars import UTCInterval
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.simulation.randomness import random_stream

pytestmark = pytest.mark.unit


def span(start: str, end: str) -> UTCInterval:
    return UTCInterval(
        datetime.fromisoformat(start).replace(tzinfo=UTC), datetime.fromisoformat(end).replace(tzinfo=UTC)
    )


def templates(count: int) -> tuple[WeekTemplate, ...]:
    return tuple(
        WeekTemplate(
            date(2025, 1, 6) + timedelta(weeks=i),
            (
                TemplateArrival(timedelta(hours=9), f"author-{i}", WorkOrigin.HUMAN),
                TemplateArrival(timedelta(hours=9, minutes=3), f"bot-{i}", WorkOrigin.UNKNOWN),
            ),
        )
        for i in range(count)
    )


def test_whole_weeks_with_replacement_and_bundled_attributes() -> None:
    source = templates(8)
    result = generate_proposals(
        source, span=span("2026-01-05", "2026-03-16"), timezone="UTC", root_seed=7, replication=2
    )
    assert result.limitations == ()
    assert len(result.proposals) == 20
    selected = []
    for week in range(10):
        first, second = result.proposals[week * 2 : week * 2 + 2]
        index = int(first.author_id.split("-")[1])
        selected.append(index)
        assert second.author_id == f"bot-{index}"
        assert (first.origin, second.origin) == (WorkOrigin.HUMAN, WorkOrigin.UNKNOWN)
        assert first.ready_at == week * 604800 + 32400
        assert second.ready_at - first.ready_at == 180
    assert len(set(selected)) > 1
    assert len(set(selected)) < 10


@pytest.mark.parametrize("count,flags", [(1, ("exploratory_only",)), (7, ("exploratory_only",)), (8, ())])
def test_complete_week_threshold_includes_empty_weeks(count: int, flags: tuple[str, ...]) -> None:
    source = tuple(WeekTemplate(t.week_start, ()) for t in templates(count))
    result = generate_proposals(
        source, span=span("2026-01-05", "2026-01-12"), timezone="UTC", root_seed=0, replication=0
    )
    assert result.proposals == ()
    assert result.limitations == flags


def test_wall_time_dst_and_half_open_clipping() -> None:
    source = (
        WeekTemplate(
            date(2025, 1, 6),
            (
                TemplateArrival(timedelta(days=6, hours=9), "human", WorkOrigin.HUMAN),
                TemplateArrival(timedelta(days=6, hours=10), "ai", WorkOrigin.AI),
            ),
        ),
    )
    result = generate_proposals(
        source, span=span("2026-03-29T07:00", "2026-04-05T08:00"), timezone="Europe/Berlin", root_seed=0, replication=0
    )
    assert [p.ready_at for p in result.proposals] == [0, 3600, 604800]
    assert [p.origin for p in result.proposals] == [WorkOrigin.HUMAN, WorkOrigin.AI, WorkOrigin.HUMAN]


@pytest.mark.parametrize(
    "timezone,start,end,offset,expected",
    [
        ("America/New_York", "2026-01-05T01:00", "2026-01-05T03:00", timedelta(days=6, hours=21), 3600),
        ("Asia/Tokyo", "2026-01-04T14:00", "2026-01-04T16:00", timedelta(), 3600),
    ],
)
def test_week_boundaries_use_declared_zone(
    timezone: str, start: str, end: str, offset: timedelta, expected: int
) -> None:
    source = (WeekTemplate(date(2025, 1, 6), (TemplateArrival(offset, "a", WorkOrigin.NON_AI_AUTOMATION),)),)
    result = generate_proposals(source, span=span(start, end), timezone=timezone, root_seed=0, replication=0)
    assert len(result.proposals) == 1
    assert result.proposals[0].ready_at == expected
    assert result.proposals[0].origin is WorkOrigin.NON_AI_AUTOMATION


@pytest.mark.parametrize("start,end", [("2026-03-23", "2026-03-30"), ("2026-10-19", "2026-10-26")])
def test_dst_gap_and_fold_rejected(start: str, end: str) -> None:
    source = (
        WeekTemplate(
            date(2025, 1, 6), (TemplateArrival(timedelta(days=6, hours=2, minutes=30), "a", WorkOrigin.UNKNOWN),)
        ),
    )
    with pytest.raises(ValueError, match="nonexistent|ambiguous"):
        generate_proposals(source, span=span(start, end), timezone="Europe/Berlin", root_seed=0, replication=0)


def test_week_start_at_horizon_is_not_sampled() -> None:
    source = (
        WeekTemplate(
            date(2025, 1, 6), (TemplateArrival(timedelta(days=6, hours=2, minutes=30), "a", WorkOrigin.UNKNOWN),)
        ),
    )
    # The excluded following week contains a nonexistent Sunday 02:30.
    result = generate_proposals(
        source, span=span("2026-03-15T23:00", "2026-03-22T23:00"), timezone="Europe/Berlin", root_seed=0, replication=0
    )
    assert len(result.proposals) == 1
    assert result.proposals[0].ready_at == 527400


@pytest.mark.property
@given(seed=st.integers(0, 2**32), replication=st.integers(0, 100))
def test_stable_proposals_and_latents(seed: int, replication: int) -> None:
    source = templates(8)
    bounds = span("2026-01-05", "2026-02-02")
    first = generate_proposals(source, span=bounds, timezone="UTC", root_seed=seed, replication=replication)
    random_stream(seed, replication, "unrelated").random(100)
    second = generate_proposals(
        tuple(reversed(source)), span=bounds, timezone="UTC", root_seed=seed, replication=replication
    )
    assert first == second
    assert len({p.pr_id for p in first.proposals}) == len(first.proposals)
    assert [random_stream(seed, replication, p.pr_id, 1, "service").random() for p in first.proposals] == [
        random_stream(seed, replication, p.pr_id, 1, "service").random() for p in second.proposals
    ]


@pytest.mark.parametrize("offset", [timedelta(microseconds=-1), timedelta(days=7)])
def test_invalid_offsets(offset: timedelta) -> None:
    with pytest.raises(ValueError, match="offset"):
        TemplateArrival(offset, "a", WorkOrigin.HUMAN)


def test_invalid_templates() -> None:
    with pytest.raises(ValueError, match="author"):
        TemplateArrival(timedelta(), "", WorkOrigin.HUMAN)
    with pytest.raises(ValueError, match="Monday"):
        WeekTemplate(date(2025, 1, 7), ())
    for source in ((), (templates(1)[0], templates(1)[0])):
        with pytest.raises(ValueError, match="unique|at least one"):
            generate_proposals(
                source, span=span("2026-01-05", "2026-01-12"), timezone="UTC", root_seed=0, replication=0
            )
