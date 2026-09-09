"""Typed contracts for the deterministic pull-request lifecycle."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import ClassVar


class WorkOrigin(StrEnum):
    """Declared origin of a pull request; actor kind is modeled separately."""

    HUMAN = "human"
    AI = "ai"
    NON_AI_AUTOMATION = "non_ai_automation"
    UNKNOWN = "unknown"


class PullRequestState(StrEnum):
    """A pull request's position in the modeled review workflow."""

    READY = "ready"
    VERIFYING = "verifying"
    AUTHOR_RESPONSE = "author_response"
    QUEUED_FOR_REVIEW = "queued_for_review"
    IN_REVIEW = "in_review"
    APPROVED_WAITING_MERGE = "approved_waiting_merge"
    MERGED = "merged"
    CLOSED_WITHOUT_MERGE = "closed_without_merge"
    UNRESOLVED = "unresolved"


class TerminalReason(StrEnum):
    """Why a pull request stopped progressing in a replication."""

    MERGED = "merged"
    CLOSED_WITHOUT_MERGE = "closed_without_merge"
    ABANDONED = "abandoned"
    HORIZON = "horizon"


class LifecycleEvent(StrEnum):
    """Deterministic events accepted by the pull-request state machine."""

    START_VERIFICATION = "start_verification"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    REVISION_SUBMITTED = "revision_submitted"
    REVIEW_STARTED = "review_started"
    REVIEW_APPROVED = "review_approved"
    CHANGES_REQUESTED = "changes_requested"
    REVIEW_BYPASSED = "review_bypassed"
    MERGE_COMPLETED = "merge_completed"
    CLOSED = "closed"
    ABANDONED = "abandoned"
    HORIZON_REACHED = "horizon_reached"


class TransitionError(ValueError):
    """Raised when an event is invalid for the current lifecycle state."""


_TERMINAL_TRANSITIONS = {
    LifecycleEvent.CLOSED: PullRequestState.CLOSED_WITHOUT_MERGE,
    LifecycleEvent.ABANDONED: PullRequestState.CLOSED_WITHOUT_MERGE,
    LifecycleEvent.HORIZON_REACHED: PullRequestState.UNRESOLVED,
}

_TERMINAL_REASONS = {
    LifecycleEvent.MERGE_COMPLETED: TerminalReason.MERGED,
    LifecycleEvent.CLOSED: TerminalReason.CLOSED_WITHOUT_MERGE,
    LifecycleEvent.ABANDONED: TerminalReason.ABANDONED,
    LifecycleEvent.HORIZON_REACHED: TerminalReason.HORIZON,
}


@dataclass(frozen=True, slots=True)
class PullRequest:
    """Immutable state and accounting for one simulated pull request."""

    pr_id: str
    author_id: str
    origin: WorkOrigin
    ready_at: float
    state: PullRequestState = PullRequestState.READY
    revision: int = 1
    first_review_at: float | None = None
    terminal_at: float | None = None
    terminal_reason: TerminalReason | None = None
    review_visit_count: int = 0
    requested_change_count: int = 0
    verification_count: int = 0
    verified_revision: int | None = None
    approved_revision: int | None = None
    queue_entered_at: float | None = None
    queue_wait_seconds: float = 0.0
    active_review_seconds: float = 0.0
    bypass_eligible: bool = False
    bypass_audited: bool = False
    review_bypassed: bool = False
    abandonment_deadline: float | None = None
    _last_transition_at: float | None = None

    _TRANSITIONS: ClassVar[dict[PullRequestState, dict[LifecycleEvent, PullRequestState]]] = {
        PullRequestState.READY: {
            LifecycleEvent.START_VERIFICATION: PullRequestState.VERIFYING,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.VERIFYING: {
            LifecycleEvent.VERIFICATION_PASSED: PullRequestState.QUEUED_FOR_REVIEW,
            LifecycleEvent.VERIFICATION_FAILED: PullRequestState.AUTHOR_RESPONSE,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.AUTHOR_RESPONSE: {
            LifecycleEvent.REVISION_SUBMITTED: PullRequestState.VERIFYING,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.QUEUED_FOR_REVIEW: {
            LifecycleEvent.REVIEW_STARTED: PullRequestState.IN_REVIEW,
            LifecycleEvent.REVIEW_BYPASSED: PullRequestState.APPROVED_WAITING_MERGE,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.IN_REVIEW: {
            LifecycleEvent.REVIEW_APPROVED: PullRequestState.APPROVED_WAITING_MERGE,
            LifecycleEvent.CHANGES_REQUESTED: PullRequestState.AUTHOR_RESPONSE,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.APPROVED_WAITING_MERGE: {
            LifecycleEvent.MERGE_COMPLETED: PullRequestState.MERGED,
            LifecycleEvent.REVISION_SUBMITTED: PullRequestState.VERIFYING,
            **_TERMINAL_TRANSITIONS,
        },
        PullRequestState.MERGED: {},
        PullRequestState.CLOSED_WITHOUT_MERGE: {},
        PullRequestState.UNRESOLVED: {},
    }

    def __post_init__(self) -> None:
        if not self.pr_id or not self.author_id:
            raise ValueError("pull request and author identifiers must not be empty")
        self._validate_time("ready_at", self.ready_at)
        for name, value in (
            ("first_review_at", self.first_review_at),
            ("terminal_at", self.terminal_at),
            ("queue_entered_at", self.queue_entered_at),
            ("abandonment_deadline", self.abandonment_deadline),
            ("last_transition_at", self._last_transition_at),
        ):
            if value is not None:
                self._validate_time(name, value)
                if value < self.ready_at:
                    raise ValueError(f"{name} cannot be before readiness")
        if self.abandonment_deadline is not None and self.abandonment_deadline <= self.ready_at:
            raise ValueError("abandonment_deadline must be after readiness")
        if self.revision < 1:
            raise ValueError("revision must be positive")
        for name, value in (
            ("review_visit_count", self.review_visit_count),
            ("requested_change_count", self.requested_change_count),
            ("verification_count", self.verification_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be nonnegative")
        for name, value in (
            ("queue_wait_seconds", self.queue_wait_seconds),
            ("active_review_seconds", self.active_review_seconds),
        ):
            self._validate_duration(name, value)
        for name, value in (
            ("verified_revision", self.verified_revision),
            ("approved_revision", self.approved_revision),
        ):
            if value is not None and not 1 <= value <= self.revision:
                raise ValueError(f"{name} must identify an existing revision")
        self._validate_terminal_contract()
        self._validate_timestamp_chronology()
        if self.queue_entered_at is not None and self.state is not PullRequestState.QUEUED_FOR_REVIEW:
            raise ValueError("queue_entered_at requires queued_for_review state")
        if self.review_bypassed and (not self.bypass_eligible or self.bypass_audited):
            raise ValueError("recorded bypass requires eligibility and no audit")
        if self.review_bypassed and not self.verification_valid:
            raise ValueError("recorded bypass requires current verification")
        if self.review_bypassed and self.state not in {
            PullRequestState.APPROVED_WAITING_MERGE,
            PullRequestState.MERGED,
            PullRequestState.CLOSED_WITHOUT_MERGE,
            PullRequestState.UNRESOLVED,
        }:
            raise ValueError("recorded bypass requires an approved or terminal state")
        if self.state is PullRequestState.APPROVED_WAITING_MERGE and not (
            self.verification_valid and (self.approval_valid or self.review_bypassed)
        ):
            raise ValueError("approved state requires current verification and review approval or bypass")
        if self.state is PullRequestState.MERGED and not (
            self.verification_valid and (self.approval_valid or self.review_bypassed)
        ):
            raise ValueError("merged state requires current verification and review approval or bypass")

    @property
    def last_transition_at(self) -> float:
        """Timestamp of the latest transition, or readiness before the first event."""

        if self._last_transition_at is not None:
            return self._last_transition_at
        return self.ready_at if self.terminal_at is None else self.terminal_at

    @property
    def terminal(self) -> bool:
        """Whether no later lifecycle event may change this pull request."""

        return self.state in {
            PullRequestState.MERGED,
            PullRequestState.CLOSED_WITHOUT_MERGE,
            PullRequestState.UNRESOLVED,
        }

    @property
    def censored(self) -> bool:
        """Whether observation ended before the pull request resolved."""

        return self.terminal_reason is TerminalReason.HORIZON

    @property
    def verification_valid(self) -> bool:
        """Whether verification passed for the current revision."""

        return self.verified_revision == self.revision

    @property
    def approval_valid(self) -> bool:
        """Whether human review approved the current revision."""

        return self.approved_revision == self.revision

    def transition(self, event: LifecycleEvent, *, at: float) -> PullRequest:
        """Apply one valid event and return the resulting immutable contract."""

        self._validate_transition_time(at)
        target = self._TRANSITIONS[self.state].get(event)
        if target is None:
            raise TransitionError(f"{self.state.value} cannot handle {event.value}")

        if event is LifecycleEvent.REVIEW_BYPASSED and (not self.bypass_eligible or self.bypass_audited):
            raise TransitionError("review bypass requires eligibility and no audit")
        if event is LifecycleEvent.MERGE_COMPLETED and not (
            self.verification_valid and (self.approval_valid or self.review_bypassed)
        ):
            raise TransitionError("merge requires current verification and review approval or bypass")

        if event in _TERMINAL_REASONS:
            return self._terminate(event, target=target, at=at)
        if event is LifecycleEvent.START_VERIFICATION:
            return replace(
                self,
                state=target,
                verification_count=self.verification_count + 1,
                _last_transition_at=at,
            )
        if event is LifecycleEvent.VERIFICATION_PASSED:
            return replace(
                self,
                state=target,
                verified_revision=self.revision,
                queue_entered_at=at,
                _last_transition_at=at,
            )
        if event is LifecycleEvent.VERIFICATION_FAILED:
            return replace(self, state=target, _last_transition_at=at)
        if event is LifecycleEvent.REVISION_SUBMITTED:
            return replace(
                self,
                state=target,
                revision=self.revision + 1,
                verification_count=self.verification_count + 1,
                verified_revision=None,
                approved_revision=None,
                queue_entered_at=None,
                review_bypassed=False,
                _last_transition_at=at,
            )
        if event is LifecycleEvent.REVIEW_STARTED:
            if self.queue_entered_at is None or not self.verification_valid:
                raise TransitionError("review requires a verified revision in the review queue")
            return replace(
                self,
                state=target,
                first_review_at=self.first_review_at if self.first_review_at is not None else at,
                review_visit_count=self.review_visit_count + 1,
                queue_wait_seconds=self.queue_wait_seconds + at - self.queue_entered_at,
                queue_entered_at=None,
                _last_transition_at=at,
            )
        if event is LifecycleEvent.REVIEW_APPROVED:
            return replace(self, state=target, approved_revision=self.revision, _last_transition_at=at)
        if event is LifecycleEvent.CHANGES_REQUESTED:
            return replace(
                self,
                state=target,
                requested_change_count=self.requested_change_count + 1,
                approved_revision=None,
                _last_transition_at=at,
            )
        if event is LifecycleEvent.REVIEW_BYPASSED:
            if not self.verification_valid:
                raise TransitionError("review bypass requires current verification")
            return replace(
                self,
                state=target,
                queue_entered_at=None,
                review_bypassed=True,
                _last_transition_at=at,
            )
        raise AssertionError(f"unhandled lifecycle event {event.value}")

    def consume_review_service(self, seconds: float) -> PullRequest:
        """Add active reviewer service without counting off-duty elapsed time."""

        self._validate_duration("review service", seconds)
        if self.state is not PullRequestState.IN_REVIEW:
            raise TransitionError("review service can only be consumed during active review")
        return replace(self, active_review_seconds=self.active_review_seconds + seconds)

    def _terminate(self, event: LifecycleEvent, *, target: PullRequestState, at: float) -> PullRequest:
        wait = self.queue_wait_seconds
        if self.queue_entered_at is not None:
            wait += at - self.queue_entered_at
        return replace(
            self,
            state=target,
            terminal_at=at,
            terminal_reason=_TERMINAL_REASONS[event],
            queue_entered_at=None,
            queue_wait_seconds=wait,
            _last_transition_at=at,
        )

    def _validate_transition_time(self, at: float) -> None:
        self._validate_time("transition time", at)
        if at < self.ready_at:
            raise ValueError("transition time cannot be before readiness")
        if at < self.last_transition_at:
            raise ValueError("transition time cannot be before the previous transition")

    def _validate_terminal_contract(self) -> None:
        if self.terminal:
            if self.terminal_at is None or self.terminal_reason is None:
                raise ValueError("terminal state requires a timestamp and reason")
        elif self.terminal_at is not None or self.terminal_reason is not None:
            raise ValueError("nonterminal state cannot have a terminal timestamp or reason")
        expected_reasons = {
            PullRequestState.MERGED: {TerminalReason.MERGED},
            PullRequestState.CLOSED_WITHOUT_MERGE: {
                TerminalReason.CLOSED_WITHOUT_MERGE,
                TerminalReason.ABANDONED,
            },
            PullRequestState.UNRESOLVED: {TerminalReason.HORIZON},
        }
        if self.terminal and self.terminal_reason not in expected_reasons[self.state]:
            raise ValueError("terminal reason does not match terminal state")

    def _validate_timestamp_chronology(self) -> None:
        if (
            self.terminal_at is not None
            and self._last_transition_at is not None
            and self.terminal_at != self._last_transition_at
        ):
            raise ValueError("terminal_at must equal the latest transition")
        if self.first_review_at is not None and self.first_review_at > self.last_transition_at:
            raise ValueError("first_review_at cannot be after the latest transition")
        if self.queue_entered_at is not None and self.queue_entered_at > self.last_transition_at:
            raise ValueError("queue_entered_at cannot be after the latest transition")

    @staticmethod
    def _validate_time(name: str, value: float) -> None:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")

    @staticmethod
    def _validate_duration(name: str, value: float) -> None:
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and nonnegative")
