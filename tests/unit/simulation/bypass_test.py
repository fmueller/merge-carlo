from dataclasses import asdict, replace

import pytest

from merge_carlo.simulation.bypass import render_bypass_report, summarize_bypass
from merge_carlo.simulation.engine import Abandonment, ReviewBypass, Reviewer, RevisionLoops, run_fifo
from merge_carlo.simulation.randomness import random_stream
from tests.unit.simulation.engine_test import pr, span

pytestmark = pytest.mark.unit


def test_zero_eligibility_reproduces_baseline() -> None:
    proposals = (pr("a"), pr("b", ready=3))
    reviewers = (Reviewer("r", (span(0, 100),)),)
    loops = RevisionLoops(2, 1, 0.3, 0.4, 0.2)
    baseline = run_fifo(proposals, reviewers, span=span(0, 100), service_seconds=7, loops=loops)
    assert (
        run_fifo(proposals, reviewers, span=span(0, 100), service_seconds=7, loops=loops, bypass=ReviewBypass(0, 0.5))
        == baseline
    )


def test_full_bypass_requires_verification_and_coordination_but_no_reviewer() -> None:
    result = run_fifo(
        (pr("a"), pr("b", ready=2)),
        (),
        span=span(0, 30),
        service_seconds=7.2,
        loops=RevisionLoops(verification_seconds=3),
        bypass=ReviewBypass(1, 0),
        coordination_seconds=4,
    )
    assert [p.terminal_at for p in result.pull_requests] == [7, 9]
    for p in result.pull_requests:
        assert p.state == "merged" and p.verification_valid and p.review_bypassed
        assert p.first_review_at is None and p.approved_revision is None
        assert (p.review_visit_count, p.active_review_seconds, p.queue_wait_seconds) == (0, 0, 0)
    assert result.limitations == ()
    summary = summarize_bypass(result)
    assert (summary.eligible_count, summary.audited_count, summary.merges_without_human_review) == (2, 0, 2)
    assert summary.unreviewed_merge_share == 1
    assert summary.modeled_review_effort_avoided_seconds == 16
    data = asdict(summary)
    for field in ("defect_escape_rate", "security_risk_change", "policy_safety"):
        assert data[field] is None
        assert data[f"{field}_reason"] == "unsupported_in_v0_1"
    report = render_bypass_report(summary)
    assert "does not establish policy safety" in report
    assert "not an estimate of net engineering benefit" in report
    assert "assumed" in report and "16" in report


def test_labels_and_full_audit_follow_normal_review() -> None:
    proposals = (replace(pr("a"), bypass_eligible=True), pr("b"))
    reviewers = (Reviewer("r", (span(0, 30),)),)
    result = run_fifo(
        proposals, reviewers, span=span(0, 30), service_seconds=5, bypass=ReviewBypass(None, 1), coordination_seconds=2
    )
    assert [p.terminal_at for p in result.pull_requests] == [7, 12]
    assert [p.bypass_audited for p in result.pull_requests] == [True, False]
    assert all(p.review_visit_count == 1 and not p.review_bypassed for p in result.pull_requests)
    assert summarize_bypass(result).audited_count == 1
    assert summarize_bypass(result).modeled_review_effort_avoided_seconds == 0
    disabled = run_fifo(proposals, (), span=span(0, 30), service_seconds=5)
    assert all(p.censored for p in disabled.pull_requests)
    assert disabled.limitations == ("no_eligible_reviewer:a", "no_eligible_reviewer:b")
    labeled = run_fifo(proposals, (), span=span(0, 30), service_seconds=5, bypass=ReviewBypass(None, 0))
    assert [p.state for p in labeled.pull_requests] == ["merged", "unresolved"]
    assert labeled.limitations == ("no_eligible_reviewer:b",)
    audited = run_fifo(proposals, (), span=span(0, 30), service_seconds=5, bypass=ReviewBypass(None, 1))
    assert audited.limitations == ("no_eligible_reviewer:a", "no_eligible_reviewer:b")
    assert all(p.censored and p.review_visit_count == 0 for p in audited.pull_requests)


def test_keyed_eligibility_and_audits_are_stable_and_independent() -> None:
    proposals = tuple(pr(str(i)) for i in range(30))

    def run(fraction: float, audit: float, reverse: bool = False) -> dict[str, tuple[bool, bool]]:
        result = run_fifo(
            proposals[::-1] if reverse else proposals,
            (),
            span=span(0, 10),
            service_seconds=1,
            bypass=ReviewBypass(fraction, audit),
            root_seed=19,
            replication=3,
        )
        return {p.pr_id: (p.bypass_eligible, p.bypass_audited) for p in result.pull_requests}

    expected = {}
    for p in proposals:
        eligible = random_stream(19, 3, p.pr_id, "bypass-eligibility").random() < 0.6
        audited = eligible and random_stream(19, 3, p.pr_id, "bypass-audit").random() < 0.4
        expected[p.pr_id] = (bool(eligible), bool(audited))
    assert run(0.6, 0.4) == expected == run(0.6, 0.4, True)
    assert set(expected.values()) == {(True, True), (True, False), (False, False)}
    larger = run(0.9, 0.4)
    assert all(larger[key] == value for key, value in expected.items() if value[0])
    assert all(run(0.6, 0.9)[key][0] == value[0] for key, value in expected.items())


@pytest.mark.parametrize("eligible_fraction,audit_fraction,flags", [(0.5, 1, (False, False)), (1, 0.5, (True, False))])
def test_bypass_fraction_thresholds_are_exclusive(
    eligible_fraction: float, audit_fraction: float, flags: tuple[bool, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    from typing import cast

    from numpy.random import Generator

    class Draw:
        def random(self) -> float:
            return 0.5

    def stream(seed: int, replication: int, *key: str | int) -> Generator:
        return cast(Generator, Draw())

    monkeypatch.setattr("merge_carlo.simulation.engine.random_stream", stream)
    result = run_fifo(
        (pr("a"),),
        (),
        span=span(0, 10),
        service_seconds=1,
        bypass=ReviewBypass(eligible_fraction, audit_fraction),
    )
    p = result.pull_requests[0]
    assert (p.bypass_eligible, p.bypass_audited) == flags
    assert p.review_bypassed is (flags == (True, False))


@pytest.mark.parametrize("deadline,horizon,reason", [(7, 20, "abandoned"), (20, 7, "horizon"), (8, 20, "merged")])
def test_bypass_merge_obeys_competing_boundaries(deadline: float, horizon: float, reason: str) -> None:
    result = run_fifo(
        (pr("a"),),
        (),
        span=span(0, horizon),
        service_seconds=5,
        loops=RevisionLoops(verification_seconds=3),
        bypass=ReviewBypass(1, 0),
        coordination_seconds=4,
        abandonment=Abandonment(1, (deadline,)),
    )
    assert result.pull_requests[0].terminal_reason == reason
    summary = summarize_bypass(result)
    assert summary.merges_without_human_review == (reason == "merged")
    assert summary.unreviewed_merge_share == (1 if reason == "merged" else None)
    assert summary.unreviewed_merge_share_reason == (None if reason == "merged" else "no_merges")
    assert all(
        b.arrivals == b.merges + b.closed_without_merge + b.unresolved + b.work_in_progress for b in result.boundaries
    )


def test_failed_verification_never_bypasses_and_truncated_summary_is_rejected() -> None:
    result = run_fifo(
        (pr("a"),),
        (),
        span=span(0, 20),
        service_seconds=5,
        bypass=ReviewBypass(1, 0),
        loops=RevisionLoops(verification_failure_probability=1, max_verification_attempts=2),
    )
    assert result.engine_truncated
    assert not result.pull_requests[0].review_bypassed
    assert result.modeled_review_effort_avoided_seconds == 0
    with pytest.raises(ValueError, match="truncated"):
        summarize_bypass(result)


def test_mixed_outcomes_report_uses_all_merges_not_eligible_work_as_denominator() -> None:
    result = run_fifo(
        (replace(pr("a"), bypass_eligible=True), pr("b"), pr("c"), pr("d", ready=19)),
        (Reviewer("r", (span(0, 20),)),),
        span=span(0, 20),
        service_seconds=5,
        bypass=ReviewBypass(None, 0),
    )
    assert [p.state for p in result.pull_requests] == ["merged", "merged", "merged", "unresolved"]
    summary = summarize_bypass(result)
    assert summary.unreviewed_merge_share == 1 / 3
    assert render_bypass_report(summary) == (
        "Hypothetical review bypass (assumed eligibility, audit and effort).\n"
        "The model does not establish policy safety or estimate escaped defects.\n"
        "Removing review also removes modeled review-requested changes; flow gain is "
        "not an estimate of net engineering benefit. No real GitHub action is taken.\n"
        "Avoided effort is one assumed review visit per bypass, not a paired baseline saving; "
        "counts cover admitted work over the whole run.\n"
        "- eligible_count: 1\n"
        "- audited_count: 0\n"
        "- merges_without_human_review: 1\n"
        "- unreviewed_merge_share: 0.3333333333333333\n"
        "- unreviewed_merge_share_reason: null\n"
        "- modeled_review_effort_avoided_seconds: 5.0\n"
        "- defect_escape_rate: null\n"
        "- defect_escape_rate_reason: unsupported_in_v0_1\n"
        "- security_risk_change: null\n"
        "- security_risk_change_reason: unsupported_in_v0_1\n"
        "- policy_safety: null\n"
        "- policy_safety_reason: unsupported_in_v0_1\n"
    )


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_bypass_fractions(value: float) -> None:
    with pytest.raises(ValueError, match="fraction"):
        ReviewBypass(value, 0)
    with pytest.raises(ValueError, match="fraction"):
        ReviewBypass(0, value)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_coordination_delay(value: float) -> None:
    with pytest.raises(ValueError, match="coordination"):
        run_fifo((), (), span=span(0, 10), service_seconds=1, coordination_seconds=value)
