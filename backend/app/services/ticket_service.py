"""
summary:
    Ticket business logic.

    Pattern: route handlers call these functions and nothing more. Every
    significant operation:
    - runs in a transaction
    - emits an audit event
    - enqueues async jobs for notifications (does NOT block the HTTP
      response)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from ..extensions import db
from ..models.ticket import Ticket
from ..models.comment import Comment
from ..models.user import User
from ..repositories import ticket_repository as tr
from ..common.errors import ValidationError, NotFound, Forbidden
from . import workflow, audit_service
from ..tasks.notifications import notify_event


def create_ticket(
    *,
    tenant_id: str,
    actor_id: str,
    title: str,
    description: str,
    priority: str = "normal",
    category_id: Optional[str] = None,
    queue_id: Optional[str] = None,
    custom_fields: Optional[dict] = None,
) -> Ticket:
    """
    summary:
        Create a new ticket in `open` status. Allocates a tenant-scoped
        readable number, writes an audit event and enqueues a creation
        notification.
    args:
        tenant_id: tenant scope.
        actor_id: id of the user creating (and requesting) the ticket.
        title: short summary, mandatory.
        description: full description, mandatory.
        priority: one of low/normal/high/urgent.
        category_id: optional category id.
        queue_id: optional queue id.
        custom_fields: optional dict of tenant-defined fields.
    return:
        The persisted Ticket instance.
    """
    if not title or not title.strip():
        raise ValidationError("Title is required", field="title")
    if not description or not description.strip():
        raise ValidationError("Description is required", field="description")
    if priority not in ("low", "normal", "high", "urgent"):
        raise ValidationError("Invalid priority", field="priority")

    number = tr.next_ticket_number(tenant_id)

    ticket = Ticket(
        tenant_id=tenant_id,
        number=number,
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        status="open",
        requester_id=actor_id,
        category_id=category_id,
        queue_id=queue_id,
        custom_fields=custom_fields or {},
        source="web",
    )
    db.session.add(ticket)
    db.session.flush()  # needed so the audit event can reference ticket.id

    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        ticket_id=ticket.id,
        event_type="ticket.created",
        payload={"number": number, "title": ticket.title, "priority": priority},
    )

    db.session.commit()

    # CRITIQUE: enqueue happens after commit. If the broker is down the
    # notification is lost. Robust solution: outbox pattern (write a row
    # to an `outbox_events` table inside the same transaction, then a
    # worker drains via polling/LISTEN). The scaffold uses direct enqueue.
    notify_event.delay("ticket.created", ticket.id)

    return ticket


def add_comment(
    *,
    tenant_id: str,
    actor_id: str,
    ticket_id: str,
    body: str,
    is_internal: bool,
    actor_permissions: set[str],
) -> Comment:
    """
    summary:
        Append a comment to a ticket and update the relevant
        denormalized timestamps. Internal comments require the
        `ticket.comment_internal` permission.
    args:
        tenant_id: tenant scope.
        actor_id: id of the comment author.
        ticket_id: target ticket id.
        body: comment text, mandatory.
        is_internal: True for internal-only visibility.
        actor_permissions: permission codes effective for the actor.
    return:
        The persisted Comment instance.
    """
    if not body or not body.strip():
        raise ValidationError("Empty comment", field="body")

    if is_internal and "ticket.comment_internal" not in actor_permissions:
        raise Forbidden("Permission denied for internal comment")

    ticket = tr.get_by_id(tenant_id, ticket_id)

    c = Comment(
        tenant_id=tenant_id,
        ticket_id=ticket.id,
        author_id=actor_id,
        body=body.strip(),
        is_internal=is_internal,
    )
    db.session.add(c)

    # touch the ticket for denormalized fields
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if is_internal:
        ticket.last_internal_update_at = now
    else:
        ticket.last_public_reply_at = now

    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        ticket_id=ticket.id,
        event_type="ticket.commented",
        payload={"is_internal": is_internal},
    )

    db.session.commit()

    if not is_internal:
        notify_event.delay("ticket.commented", ticket.id)

    return c


def assign(
    *,
    tenant_id: str,
    actor_id: str,
    ticket_id: str,
    assignee_id: Optional[str],
) -> Ticket:
    """
    summary:
        Set or clear the assignee of a ticket.
    args:
        tenant_id: tenant scope.
        actor_id: id of the user performing the assignment.
        ticket_id: target ticket id.
        assignee_id: new assignee id, or None to unassign.
    return:
        The updated Ticket instance.
    """
    ticket = tr.get_by_id(tenant_id, ticket_id)

    if assignee_id:
        # tenant guarantee: cannot assign to a user from another tenant
        u = db.session.execute(
            select(User).where(User.id == assignee_id, User.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if not u:
            raise NotFound("Assignee not found within this tenant")

    prev = ticket.assignee_id
    ticket.assignee_id = assignee_id

    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        ticket_id=ticket.id,
        event_type="ticket.assigned",
        payload={"from": prev, "to": assignee_id},
    )
    db.session.commit()
    notify_event.delay("ticket.assigned", ticket.id)
    return ticket


def transition(
    *,
    tenant_id: str,
    actor_id: str,
    ticket_id: str,
    to_status: str,
    reason: Optional[str],
    actor_permissions: set[str],
) -> Ticket:
    """
    summary:
        Move a ticket to a new status, applying permission gates that the
        pure workflow module does not know about.
    args:
        tenant_id: tenant scope.
        actor_id: id of the user requesting the transition.
        ticket_id: target ticket id.
        to_status: requested next status.
        reason: optional reason text. Required for resolved/cancelled.
        actor_permissions: permission codes effective for the actor.
    return:
        The updated Ticket instance.
    """
    ticket = tr.get_by_id(tenant_id, ticket_id)

    # Permission gate: a few transitions require dedicated permissions.
    # workflow.py is "pure" (no permission knowledge); the gate lives here.
    if to_status == "reopened" and ticket.status == "closed":
        if "ticket.reopen_closed" not in actor_permissions:
            raise Forbidden("ticket.reopen_closed permission required")
    if to_status == "reopened" and ticket.status == "resolved":
        if "ticket.reopen" not in actor_permissions:
            raise Forbidden("ticket.reopen permission required")

    prev, new = workflow.apply_transition(ticket, to_status, reason=reason)

    audit_service.record(
        tenant_id=tenant_id,
        actor_id=actor_id,
        ticket_id=ticket.id,
        event_type="ticket.transition",
        payload={"from": prev, "to": new, "reason": reason},
    )

    db.session.commit()

    notify_event.delay(
        f"ticket.{new}" if new in ("resolved", "closed", "reopened", "cancelled") else "ticket.updated",
        ticket.id,
    )

    return ticket
