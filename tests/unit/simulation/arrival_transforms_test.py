from dataclasses import replace
from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.arrivals import AdditiveAI, ReplacementAI, TemplateArrival, WeekTemplate, generate_proposals
from merge_carlo.simulation.domain import WorkOrigin
from merge_carlo.simulation.randomness import random_stream
from tests.unit.simulation.arrivals_test import span

pytestmark = pytest.mark.unit

SOURCE = (
    WeekTemplate(
        date(2025, 1, 6),
        tuple(TemplateArrival(timedelta(hours=i + 1), f"author-{i}", origin) for i, origin in enumerate(WorkOrigin)),
    ),
)


@pytest.mark.property
@given(seed=st.integers(0, 2**32), replication=st.integers(0, 100), fraction=st.floats(0, 3))
def test_additive_preserves_baseline_and_stable_prefix(seed: int, replication: int, fraction: float) -> None:
    bounds = span("2026-01-05", "2026-01-19")
    baseline = generate_proposals(SOURCE, span=bounds, timezone="UTC", root_seed=seed, replication=replication)
    small, large = (
        generate_proposals(
            SOURCE, span=bounds, timezone="UTC", root_seed=seed, replication=replication, scenario=AdditiveAI(f)
        )
        for f in (fraction, fraction + 1)
    )
    assert set(baseline.proposals) <= set(small.proposals) <= set(large.proposals)
    assert small.limitations == baseline.limitations
    for week in ("2026-01-05", "2026-01-12"):
        added = [p for p in small.proposals if p.pr_id.startswith(f"ai-additive:{week}:")]
        draw = random_stream(seed, replication, "ai-additive-count", week).random()
        assert len(added) == int(4 * fraction + draw)
        assert all(p.origin is WorkOrigin.AI for p in added)
        assert len({p.pr_id for p in added}) == len(added)
        assert {p.author_id for p in added} <= {a.author_id for a in SOURCE[0].arrivals}
        assert all(p.ready_at % 604800 in (3600, 7200, 10800, 14400) for p in added)


@pytest.mark.property
@given(seed=st.integers(0, 2**32), fraction=st.floats(0, 1))
def test_replacement_changes_only_known_human_origin(seed: int, fraction: float) -> None:
    bounds = span("2026-01-05", "2026-01-19")
    baseline = generate_proposals(SOURCE, span=bounds, timezone="UTC", root_seed=seed, replication=3)
    result = generate_proposals(
        SOURCE, span=bounds, timezone="UTC", root_seed=seed, replication=3, scenario=ReplacementAI(fraction)
    )
    assert len(result.proposals) == len(baseline.proposals)
    for before, after in zip(baseline.proposals, result.proposals, strict=True):
        selected = before.origin is WorkOrigin.HUMAN and (
            random_stream(seed, 3, before.pr_id, "ai-replacement").random() < fraction
        )
        assert after == (replace(before, origin=WorkOrigin.AI) if selected else before)
        assert (
            random_stream(seed, 3, before.pr_id, 1, "service").random()
            == random_stream(seed, 3, after.pr_id, 1, "service").random()
        )
    assert result.cohort_mix == {origin: sum(p.origin is origin for p in result.proposals) for origin in WorkOrigin}


def test_endpoints_and_suite_extension() -> None:
    bounds = span("2026-01-05", "2026-01-12")
    baseline = generate_proposals(SOURCE, span=bounds, timezone="UTC", root_seed=4, replication=2)
    scenarios: list[AdditiveAI | ReplacementAI] = [AdditiveAI(0), ReplacementAI(0), ReplacementAI(1), AdditiveAI(0.75)]
    original = [
        generate_proposals(SOURCE, span=bounds, timezone="UTC", root_seed=4, replication=2, scenario=s)
        for s in scenarios
    ]
    assert original[:2] == [baseline, baseline]
    assert original[2].cohort_mix == {
        WorkOrigin.HUMAN: 0,
        WorkOrigin.AI: 2,
        WorkOrigin.NON_AI_AUTOMATION: 1,
        WorkOrigin.UNKNOWN: 1,
    }
    extended = {
        s: generate_proposals(SOURCE, span=bounds, timezone="UTC", root_seed=4, replication=2, scenario=s)
        for s in [AdditiveAI(2), *reversed(scenarios)]
    }
    assert [extended[s] for s in scenarios] == original


@pytest.mark.parametrize("fraction", [-0.01, float("nan"), float("inf"), -float("inf")])
def test_invalid_fractions(fraction: float) -> None:
    for kind in (AdditiveAI, ReplacementAI):
        with pytest.raises(ValueError, match="fraction"):
            kind(fraction)


def test_replacement_above_one_rejected() -> None:
    with pytest.raises(ValueError, match="fraction"):
        ReplacementAI(1.01)


def test_empty_weeks_and_half_open_additive_clipping() -> None:
    bounds = span("2026-01-05T02:00", "2026-01-05T04:00")
    result = generate_proposals(
        SOURCE, span=bounds, timezone="UTC", root_seed=0, replication=0, scenario=AdditiveAI(10)
    )
    assert all(0 <= p.ready_at < 7200 for p in result.proposals)
    assert {p.ready_at for p in result.proposals if p.origin is WorkOrigin.AI} == {0, 3600}
    empty = generate_proposals(
        (WeekTemplate(date(2025, 1, 6), ()),),
        span=bounds,
        timezone="UTC",
        root_seed=0,
        replication=0,
        scenario=AdditiveAI(10),
    )
    assert empty.proposals == ()
    assert empty.cohort_mix == dict.fromkeys(WorkOrigin, 0)


def test_added_templates_vary_by_week_and_ignore_input_order() -> None:
    source = (
        *SOURCE,
        WeekTemplate(date(2025, 1, 13), (TemplateArrival(timedelta(hours=8), "other-author", WorkOrigin.UNKNOWN),)),
    )
    bounds = span("2026-01-05", "2026-02-02")
    result = generate_proposals(
        source, span=bounds, timezone="UTC", root_seed=19, replication=5, scenario=AdditiveAI(10)
    )
    reordered = generate_proposals(
        tuple(reversed(source)), span=bounds, timezone="UTC", root_seed=19, replication=5, scenario=AdditiveAI(10)
    )
    assert result == reordered
    weeks = []
    for week in ("2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"):
        added = sorted(
            (p for p in result.proposals if p.pr_id.startswith(f"ai-additive:{week}:")),
            key=lambda p: int(p.pr_id.rsplit(":", 1)[1]),
        )
        weeks.append(tuple(p.author_id for p in added[:10]))
        assert {p.author_id for p in added} - {"other-author"}
        assert any(p.author_id == "other-author" for p in added)
    assert len(set(weeks)) > 1


def test_replacement_threshold_is_strict() -> None:
    fraction = float(random_stream(0, 0, "baseline:2026-01-05:0", "ai-replacement").random())
    result = generate_proposals(
        SOURCE,
        span=span("2026-01-05", "2026-01-12"),
        timezone="UTC",
        root_seed=0,
        replication=0,
        scenario=ReplacementAI(fraction),
    )
    assert result.proposals[0].origin is WorkOrigin.HUMAN
