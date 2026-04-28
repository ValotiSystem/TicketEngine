"""
summary:
    Centralized audit. Every meaningful action goes through here.

    CRITIQUE: writing AuditEvent in the same commit as the ticket is the
    minimum consistency guarantee. DO NOT use a background thread to write
    audit: if the app crashes the audit is lost.
"""
from __future__ import annotations

from typing import Any, Optional

from ..extensions import db
from ..models.audit import AuditEvent


def record(
    *,
    tenant_id: str,
    actor_id: Optional[str],
    event_type: str,
    ticket_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    """
    summary:
        Append an immutable audit event to the current SQLAlchemy session.
        The caller commits (or rolls back) the transaction.
    args:
        tenant_id: tenant the event belongs to.
        actor_id: user that performed the action; None for system actions.
        event_type: one of EVENT_TYPES (see models/audit.py).
        ticket_id: optional related ticket id.
        payload: arbitrary JSON-serializable context for the event.
    return:
        The AuditEvent instance staged on the session.
    """
    evt = AuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        ticket_id=ticket_id,
        event_type=event_type,
        payload=payload or {},
    )
    db.session.add(evt)
    return evt
