"""
summary:
    Data access layer for tickets.

    Every query passes through this module. Guarantee: every method takes
    a `tenant_id` and filters by it. No "free queries" sprinkled across
    route handlers.

    CRITIQUE: an alternative is a session-scoped filter (a `do_orm_execute`
    event listener that injects WHERE tenant_id automatically). Safer but
    more magical. The scaffold prefers explicit.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func, or_

from ..extensions import db
from ..models.ticket import Ticket, TicketNumberSequence
from ..common.errors import NotFound


def get_by_id(tenant_id: str, ticket_id: str) -> Ticket:
    """
    summary:
        Load a ticket by id, scoped to the given tenant.
    args:
        tenant_id: tenant the ticket must belong to.
        ticket_id: ticket id.
    return:
        Ticket instance. Raises NotFound when not visible to this tenant.
    """
    t = db.session.execute(
        select(Ticket).where(Ticket.tenant_id == tenant_id, Ticket.id == ticket_id)
    ).scalar_one_or_none()
    if not t:
        raise NotFound("Ticket not found")
    return t


def list_tickets(
    tenant_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    queue_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    q: Optional[str] = None,  # basic textual search
    sort: str = "-created_at",
):
    """
    summary:
        Paginated, filtered listing of tickets within a tenant.
    args:
        tenant_id: tenant scope.
        page: 1-based page number.
        page_size: page size, clamped to 1..100.
        status: optional ticket status filter.
        assignee_id: optional assignee id filter.
        queue_id: optional queue id filter.
        requester_id: optional requester id filter.
        q: optional case-insensitive search on title/description.
        sort: sort key with optional leading "-" for descending order.
            Whitelisted: created_at, updated_at, priority, status, due_at.
    return:
        Tuple (list of Ticket, total count).
    """
    stmt = select(Ticket).where(Ticket.tenant_id == tenant_id)
    count_stmt = select(func.count()).select_from(Ticket).where(Ticket.tenant_id == tenant_id)

    if status:
        stmt = stmt.where(Ticket.status == status)
        count_stmt = count_stmt.where(Ticket.status == status)
    if assignee_id:
        stmt = stmt.where(Ticket.assignee_id == assignee_id)
        count_stmt = count_stmt.where(Ticket.assignee_id == assignee_id)
    if queue_id:
        stmt = stmt.where(Ticket.queue_id == queue_id)
        count_stmt = count_stmt.where(Ticket.queue_id == queue_id)
    if requester_id:
        stmt = stmt.where(Ticket.requester_id == requester_id)
        count_stmt = count_stmt.where(Ticket.requester_id == requester_id)
    if q:
        # CRITIQUE: ILIKE on title/description does NOT scale. Once tickets
        # exceed a few hundred thousand, switch to Postgres FTS (tsvector
        # + GIN) or to an external engine (Meilisearch/OpenSearch).
        like = f"%{q}%"
        stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
        count_stmt = count_stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))

    # Sort whitelist: never accept arbitrary column names from the client
    sort_map = {
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
        "priority": Ticket.priority,
        "status": Ticket.status,
        "due_at": Ticket.due_at,
    }
    desc = sort.startswith("-")
    key = sort[1:] if desc else sort
    col = sort_map.get(key, Ticket.created_at)
    stmt = stmt.order_by(col.desc() if desc else col.asc())

    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = db.session.execute(stmt).scalars().all()
    total = db.session.execute(count_stmt).scalar_one()
    return items, total


def next_ticket_number(tenant_id: str) -> int:
    """
    summary:
        Allocate the next human-readable ticket number for a tenant.

        CRITIQUE: the correct Postgres implementation uses
        SELECT ... FOR UPDATE. SQLAlchemy expresses it via
        `with_for_update()`. On SQLite this degrades silently (FOR UPDATE
        is a no-op). Acceptable in dev because we are single-process.
    args:
        tenant_id: tenant the sequence belongs to.
    return:
        The next integer to use as ticket.number.
    """
    seq = db.session.execute(
        select(TicketNumberSequence)
        .where(TicketNumberSequence.tenant_id == tenant_id)
        .with_for_update()
    ).scalar_one_or_none()

    if not seq:
        seq = TicketNumberSequence(tenant_id=tenant_id, last_value=0)
        db.session.add(seq)
        db.session.flush()

    seq.last_value += 1
    return seq.last_value
