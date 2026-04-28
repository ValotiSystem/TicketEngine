"""
summary:
    Ticket state machine.

    Single source of truth for transitions: no handler/route may modify
    `ticket.status` without going through `apply_transition()`.

    CRITIQUE notes vs the original spec:
    1. The spec allowed `waiting_on_requester -> reopened`. Removed: only
       `resolved`/`closed` should transition to `reopened`. From `waiting_*`
       you go back to `in_progress` or cancel.
    2. The spec did not allow `triage -> resolved` but in practice an agent
       in triage can mark a ticket as duplicate / already fixed. Added.
    3. `cancelled` stays terminal: the spec said "unless explicit policy".
       If reopening a cancelled ticket is needed, do it via dedicated
       permission later, not via a standard transition.
    4. From `closed` you go only to `reopened`, and only with the
       `ticket.reopen_closed` permission (checked in routes/services, not
       here - this function is "pure" and ignorant of permissions).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..common.errors import InvalidTransition, ValidationError


TRANSITIONS: dict[str, set[str]] = {
    "draft": {"open"},
    "open": {"triage", "cancelled"},
    "triage": {"in_progress", "waiting_on_requester", "resolved", "cancelled"},
    "in_progress": {"waiting_on_requester", "waiting_on_third_party", "resolved"},
    "waiting_on_requester": {"in_progress", "cancelled"},
    "waiting_on_third_party": {"in_progress", "cancelled"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"in_progress", "triage"},
    "cancelled": set(),
}

TERMINAL = {"cancelled"}  # closed is NOT terminal: reopening is allowed

# States that require a mandatory reason to be reached
REASON_REQUIRED = {"resolved", "cancelled"}


def can_transition(from_status: str, to_status: str) -> bool:
    """
    summary:
        Check whether a transition is allowed by the state machine.
    args:
        from_status: current status.
        to_status: candidate next status.
    return:
        True when the transition is permitted.
    """
    return to_status in TRANSITIONS.get(from_status, set())


def assert_transition(from_status: str, to_status: str) -> None:
    """
    summary:
        Raise InvalidTransition when the transition is not allowed.
    args:
        from_status: current status.
        to_status: candidate next status.
    return:
        None.
    """
    if from_status == to_status:
        raise InvalidTransition(f"Already in status {from_status}")
    if not can_transition(from_status, to_status):
        raise InvalidTransition(
            f"Transition not allowed: {from_status} -> {to_status}"
        )


def apply_transition(ticket, to_status: str, *, reason: Optional[str] = None):
    """
    summary:
        Mutate timestamps and reason fields based on the new status.
        Does not commit; the caller (service) controls the transaction.
    args:
        ticket: Ticket instance to mutate.
        to_status: target status.
        reason: optional reason text. Required for `resolved` / `cancelled`.
    return:
        Tuple (previous_status, new_status).
    """
    if to_status in REASON_REQUIRED and not (reason and reason.strip()):
        raise ValidationError(f"Reason required to transition to {to_status}", field="reason")

    assert_transition(ticket.status, to_status)

    now = datetime.now(timezone.utc)
    prev = ticket.status
    ticket.status = to_status

    if to_status == "resolved":
        ticket.resolved_at = now
        ticket.resolution_reason = reason
    elif to_status == "closed":
        ticket.closed_at = now
    elif to_status == "reopened":
        # Clear closure/resolution timestamps: the ticket is "alive" again
        ticket.resolved_at = None
        ticket.closed_at = None
    elif to_status == "cancelled":
        ticket.resolution_reason = reason

    return prev, to_status
