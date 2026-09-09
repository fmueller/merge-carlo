from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.domain import (
    LifecycleEvent,
    PullRequest,
    PullRequestState,
    TerminalReason,
    TransitionError,
    WorkOrigin,
)


def pull_request(
    *,
    origin: WorkOrigin = WorkOrigin.HUMAN,
    ready_at: float = 0.0,
) -> PullRequest:
    return PullRequest(
        pr_id="pr-17",
        author_id="author-4",
        origin=origin,
        ready_at=ready_at,
        bypass_eligible=True,
    )


def transition_path(*events: LifecycleEvent) -> PullRequest:
    current = pull_request()
    for at, event in enumerate(events, start=1):
        current = current.transition(event, at=float(at))
    return current


STATE_FIXTURES = {
    PullRequestState.READY: pull_request(),
    PullRequestState.VERIFYING: transition_path(LifecycleEvent.START_VERIFICATION),
    PullRequestState.AUTHOR_RESPONSE: transition_path(
        LifecycleEvent.START_VERIFICATION,
        LifecycleEvent.VERIFICATION_FAILED,
    ),
    PullRequestState.QUEUED_FOR_REVIEW: transition_path(
        LifecycleEvent.START_VERIFICATION,
        LifecycleEvent.VERIFICATION_PASSED,
    ),
    PullRequestState.IN_REVIEW: transition_path(
        LifecycleEvent.START_VERIFICATION,
        LifecycleEvent.VERIFICATION_PASSED,
        LifecycleEvent.REVIEW_STARTED,
    ),
    PullRequestState.APPROVED_WAITING_MERGE: transition_path(
        LifecycleEvent.START_VERIFICATION,
        LifecycleEvent.VERIFICATION_PASSED,
        LifecycleEvent.REVIEW_STARTED,
        LifecycleEvent.REVIEW_APPROVED,
    ),
    PullRequestState.MERGED: transition_path(
        LifecycleEvent.START_VERIFICATION,
        LifecycleEvent.VERIFICATION_PASSED,
        LifecycleEvent.REVIEW_STARTED,
        LifecycleEvent.REVIEW_APPROVED,
        LifecycleEvent.MERGE_COMPLETED,
    ),
    PullRequestState.CLOSED_WITHOUT_MERGE: transition_path(LifecycleEvent.CLOSED),
    PullRequestState.UNRESOLVED: transition_path(LifecycleEvent.HORIZON_REACHED),
}

TERMINAL_EVENTS = {
    LifecycleEvent.CLOSED: PullRequestState.CLOSED_WITHOUT_MERGE,
    LifecycleEvent.ABANDONED: PullRequestState.CLOSED_WITHOUT_MERGE,
    LifecycleEvent.HORIZON_REACHED: PullRequestState.UNRESOLVED,
}

ALLOWED_TRANSITIONS = {
    PullRequestState.READY: {LifecycleEvent.START_VERIFICATION: PullRequestState.VERIFYING, **TERMINAL_EVENTS},
    PullRequestState.VERIFYING: {
        LifecycleEvent.VERIFICATION_PASSED: PullRequestState.QUEUED_FOR_REVIEW,
        LifecycleEvent.VERIFICATION_FAILED: PullRequestState.AUTHOR_RESPONSE,
        **TERMINAL_EVENTS,
    },
    PullRequestState.AUTHOR_RESPONSE: {
        LifecycleEvent.REVISION_SUBMITTED: PullRequestState.VERIFYING,
        **TERMINAL_EVENTS,
    },
    PullRequestState.QUEUED_FOR_REVIEW: {
        LifecycleEvent.REVIEW_STARTED: PullRequestState.IN_REVIEW,
        LifecycleEvent.REVIEW_BYPASSED: PullRequestState.APPROVED_WAITING_MERGE,
        **TERMINAL_EVENTS,
    },
    PullRequestState.IN_REVIEW: {
        LifecycleEvent.REVIEW_APPROVED: PullRequestState.APPROVED_WAITING_MERGE,
        LifecycleEvent.CHANGES_REQUESTED: PullRequestState.AUTHOR_RESPONSE,
        **TERMINAL_EVENTS,
    },
    PullRequestState.APPROVED_WAITING_MERGE: {
        LifecycleEvent.MERGE_COMPLETED: PullRequestState.MERGED,
        LifecycleEvent.REVISION_SUBMITTED: PullRequestState.VERIFYING,
        **TERMINAL_EVENTS,
    },
    PullRequestState.MERGED: {},
    PullRequestState.CLOSED_WITHOUT_MERGE: {},
    PullRequestState.UNRESOLVED: {},
}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "event", "target"),
    [
        (source, event, target)
        for source, transitions in ALLOWED_TRANSITIONS.items()
        for event, target in transitions.items()
    ],
)
def test_every_declared_transition_reaches_its_target(
    source: PullRequestState,
    event: LifecycleEvent,
    target: PullRequestState,
) -> None:
    current = STATE_FIXTURES[source]

    transitioned = current.transition(event, at=current.last_transition_at + 1.0)

    assert transitioned.state is target


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "event"),
    [
        (source, event)
        for source, transitions in ALLOWED_TRANSITIONS.items()
        for event in LifecycleEvent
        if event not in transitions
    ],
)
def test_every_rejected_transition_raises_and_preserves_the_contract(
    source: PullRequestState,
    event: LifecycleEvent,
) -> None:
    current = STATE_FIXTURES[source]

    with pytest.raises(TransitionError, match="cannot handle"):
        current.transition(event, at=current.last_transition_at + 1.0)

    assert current == STATE_FIXTURES[source]


@pytest.mark.unit
def test_revision_invalidates_current_approval_and_verification() -> None:
    approved = STATE_FIXTURES[PullRequestState.APPROVED_WAITING_MERGE]
    assert approved.approval_valid
    assert approved.verification_valid

    revised = approved.transition(LifecycleEvent.REVISION_SUBMITTED, at=approved.last_transition_at + 1.0)

    assert revised.revision == approved.revision + 1
    assert not revised.approval_valid
    assert not revised.verification_valid
    assert not revised.review_bypassed
    assert revised.state is PullRequestState.VERIFYING


@pytest.mark.unit
def test_unknown_origin_round_trips_without_relabeling() -> None:
    original = pull_request(origin=WorkOrigin.UNKNOWN)

    restored = replace(original, origin=WorkOrigin(original.origin.value))

    assert restored.origin is WorkOrigin.UNKNOWN
    assert restored == original


@pytest.mark.unit
def test_horizon_censors_nonterminal_work() -> None:
    queued = STATE_FIXTURES[PullRequestState.QUEUED_FOR_REVIEW]

    unresolved = queued.transition(LifecycleEvent.HORIZON_REACHED, at=30.0)

    assert unresolved.state is PullRequestState.UNRESOLVED
    assert unresolved.terminal_reason is TerminalReason.HORIZON
    assert unresolved.terminal_at == 30.0
    assert unresolved.censored
    assert unresolved.terminal


@pytest.mark.unit
@pytest.mark.parametrize(
    ("event", "reason"),
    [
        (LifecycleEvent.CLOSED, TerminalReason.CLOSED_WITHOUT_MERGE),
        (LifecycleEvent.ABANDONED, TerminalReason.ABANDONED),
        (LifecycleEvent.MERGE_COMPLETED, TerminalReason.MERGED),
    ],
)
def test_terminal_events_record_the_distinct_reason(event: LifecycleEvent, reason: TerminalReason) -> None:
    current = (
        STATE_FIXTURES[PullRequestState.APPROVED_WAITING_MERGE]
        if event is LifecycleEvent.MERGE_COMPLETED
        else STATE_FIXTURES[PullRequestState.IN_REVIEW]
    )

    terminal = current.transition(event, at=current.last_transition_at + 1.0)

    assert terminal.terminal_reason is reason
    assert terminal.terminal_at == current.last_transition_at + 1.0
    assert terminal.terminal
    assert not terminal.censored


@pytest.mark.unit
def test_counts_timestamps_and_service_accounting_span_revisions() -> None:
    current = pull_request()
    current = current.transition(LifecycleEvent.START_VERIFICATION, at=1.0)
    current = current.transition(LifecycleEvent.VERIFICATION_PASSED, at=2.0)
    current = current.transition(LifecycleEvent.REVIEW_STARTED, at=5.0)
    current = current.consume_review_service(45.0)
    current = current.transition(LifecycleEvent.CHANGES_REQUESTED, at=50.0)
    current = current.transition(LifecycleEvent.REVISION_SUBMITTED, at=55.0)
    current = current.transition(LifecycleEvent.VERIFICATION_PASSED, at=57.0)
    current = current.transition(LifecycleEvent.REVIEW_STARTED, at=61.0)

    assert current.revision == 2
    assert current.verification_count == 2
    assert current.review_visit_count == 2
    assert current.requested_change_count == 1
    assert current.first_review_at == 5.0
    assert current.queue_wait_seconds == 7.0
    assert current.active_review_seconds == 45.0


@pytest.mark.unit
def test_bypass_requires_eligibility_and_no_audit() -> None:
    queued = STATE_FIXTURES[PullRequestState.QUEUED_FOR_REVIEW]
    ineligible = replace(queued, bypass_eligible=False)
    audited = replace(queued, bypass_audited=True)

    for current in (ineligible, audited):
        with pytest.raises(TransitionError, match="bypass"):
            current.transition(LifecycleEvent.REVIEW_BYPASSED, at=current.last_transition_at + 1.0)

    bypassed = queued.transition(LifecycleEvent.REVIEW_BYPASSED, at=queued.last_transition_at + 1.0)
    assert bypassed.review_bypassed
    assert not bypassed.approval_valid
    assert bypassed.verification_valid


@pytest.mark.unit
@pytest.mark.parametrize(
    ("event", "state", "reason"),
    [
        (LifecycleEvent.CLOSED, PullRequestState.CLOSED_WITHOUT_MERGE, TerminalReason.CLOSED_WITHOUT_MERGE),
        (LifecycleEvent.ABANDONED, PullRequestState.CLOSED_WITHOUT_MERGE, TerminalReason.ABANDONED),
        (LifecycleEvent.HORIZON_REACHED, PullRequestState.UNRESOLVED, TerminalReason.HORIZON),
    ],
)
def test_bypassed_work_can_reach_every_nonmerge_terminal_outcome(
    event: LifecycleEvent,
    state: PullRequestState,
    reason: TerminalReason,
) -> None:
    queued = STATE_FIXTURES[PullRequestState.QUEUED_FOR_REVIEW]
    bypassed = queued.transition(LifecycleEvent.REVIEW_BYPASSED, at=queued.last_transition_at + 1.0)

    terminal = bypassed.transition(event, at=bypassed.last_transition_at + 1.0)

    assert terminal.state is state
    assert terminal.terminal_reason is reason
    assert terminal.review_bypassed


@pytest.mark.unit
def test_contract_rejects_approved_and_merged_states_without_current_gates() -> None:
    approved = STATE_FIXTURES[PullRequestState.APPROVED_WAITING_MERGE]
    merged = STATE_FIXTURES[PullRequestState.MERGED]

    with pytest.raises(ValueError, match="approved state requires"):
        replace(approved, approved_revision=None)
    with pytest.raises(ValueError, match="merged state requires"):
        replace(merged, verified_revision=None)


@pytest.mark.unit
def test_contract_rejects_an_ineligible_or_audited_recorded_bypass() -> None:
    queued = STATE_FIXTURES[PullRequestState.QUEUED_FOR_REVIEW]
    bypassed = queued.transition(LifecycleEvent.REVIEW_BYPASSED, at=queued.last_transition_at + 1.0)

    with pytest.raises(ValueError, match="recorded bypass requires eligibility and no audit"):
        replace(bypassed, bypass_eligible=False)
    with pytest.raises(ValueError, match="recorded bypass requires eligibility and no audit"):
        replace(bypassed, bypass_audited=True)


@pytest.mark.unit
def test_contract_rejects_contradictory_timestamp_chronology() -> None:
    merged = STATE_FIXTURES[PullRequestState.MERGED]
    queued = STATE_FIXTURES[PullRequestState.QUEUED_FOR_REVIEW]

    with pytest.raises(ValueError, match="terminal_at must equal the latest transition"):
        replace(merged, terminal_at=merged.last_transition_at - 1.0)
    with pytest.raises(ValueError, match="first_review_at cannot be after the latest transition"):
        replace(merged, first_review_at=merged.last_transition_at + 1.0)
    with pytest.raises(ValueError, match="queue_entered_at cannot be after the latest transition"):
        replace(queued, queue_entered_at=queued.last_transition_at + 1.0)


@pytest.mark.unit
def test_service_can_only_be_consumed_during_review() -> None:
    with pytest.raises(TransitionError, match="active review"):
        pull_request().consume_review_service(1.0)

    reviewing = STATE_FIXTURES[PullRequestState.IN_REVIEW]
    with pytest.raises(ValueError, match="nonnegative"):
        reviewing.consume_review_service(-1.0)


@pytest.mark.unit
def test_transitions_reject_time_before_readiness_or_the_previous_event() -> None:
    current = pull_request(ready_at=10.0)

    with pytest.raises(ValueError, match="before readiness"):
        current.transition(LifecycleEvent.START_VERIFICATION, at=9.0)

    verifying = current.transition(LifecycleEvent.START_VERIFICATION, at=11.0)
    with pytest.raises(ValueError, match="before the previous transition"):
        verifying.transition(LifecycleEvent.VERIFICATION_PASSED, at=10.0)


@pytest.mark.property
@given(
    terminal_state=st.sampled_from(
        [
            PullRequestState.MERGED,
            PullRequestState.CLOSED_WITHOUT_MERGE,
            PullRequestState.UNRESOLVED,
        ]
    ),
    later_event=st.sampled_from(list(LifecycleEvent)),
    elapsed=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
)
def test_terminal_states_are_absorbing(
    terminal_state: PullRequestState,
    later_event: LifecycleEvent,
    elapsed: float,
) -> None:
    terminal = STATE_FIXTURES[terminal_state]

    with pytest.raises(TransitionError):
        terminal.transition(later_event, at=terminal.last_transition_at + elapsed)

    assert terminal == STATE_FIXTURES[terminal_state]
