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

from sqlalchemy import select, func, or_, text, tuple_

from ..extensions import db
from ..models.ticket import Ticket, TicketNumberSequence
from ..common.errors import NotFound
from . import cursor as cursor_codec


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
    q: Optional[str] = None,
    sort: str = "-created_at",
):
    """
    summary:
        Offset-paginated listing of tickets within a tenant. Convenient
        for the UI but does not scale to deep pages. For high-volume
        consumers prefer `list_tickets_cursor`.
    args:
        tenant_id: tenant scope.
        page: 1-based page number.
        page_size: page size, clamped to 1..100.
        status: optional ticket status filter.
        assignee_id: optional assignee id filter.
        queue_id: optional queue id filter.
        requester_id: optional requester id filter.
        q: optional full-text search term.
        sort: sort key with optional leading "-" for descending order.
            Whitelisted: created_at, updated_at, priority, status, due_at.
    return:
        Tuple (list of Ticket, total count).
    """
    stmt, count_stmt = _base_filtered(tenant_id, status, assignee_id, queue_id, requester_id, q)

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


def list_tickets_cursor(
    tenant_id: str,
    *,
    cursor: Optional[str] = None,
    page_size: int = 25,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    queue_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    q: Optional[str] = None,
):
    """
    summary:
        Keyset (cursor) paginated listing. Sort is fixed to
        (created_at DESC, id DESC) so the (tenant_id, created_at, id)
        index can serve every page in O(log N + page_size). Use this
        endpoint when you expect deep scrolling, exports, or sync
        clients.
    args:
        tenant_id: tenant scope.
        cursor: opaque cursor returned by the previous page (None for
            the first page).
        page_size: max items per page (1..200).
        status: optional ticket status filter.
        assignee_id: optional assignee id filter.
        queue_id: optional queue id filter.
        requester_id: optional requester id filter.
        q: optional full-text search term.
    return:
        Tuple (list of Ticket, next_cursor_string_or_None).
    """
    stmt, _ = _base_filtered(tenant_id, status, assignee_id, queue_id, requester_id, q)
    page_size = max(min(page_size, 200), 1)

    decoded = cursor_codec.decode(cursor)
    if decoded is not None:
        last_created, last_id = decoded
        stmt = stmt.where(tuple_(Ticket.created_at, Ticket.id) < (last_created, last_id))

    stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(page_size + 1)
    items = list(db.session.execute(stmt).scalars())

    next_cursor = None
    if len(items) > page_size:
        last = items[page_size - 1]
        items = items[:page_size]
        next_cursor = cursor_codec.encode(last.created_at, last.id)

    return items, next_cursor


def _base_filtered(
    tenant_id: str,
    status, assignee_id, queue_id, requester_id, q,
):
    """
    summary:
        Build the shared filtered SELECT and matching COUNT statements
        used by both pagination styles. Encapsulates the FTS-vs-ILIKE
        switch.
    args:
        tenant_id: tenant scope.
        status / assignee_id / queue_id / requester_id / q: optional
            filters.
    return:
        Tuple (select_stmt, count_stmt).
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
        is_postgres = db.engine.dialect.name == "postgresql"
        if is_postgres:
            # Postgres FTS via the GIN index on search_vector.
            tsq = func.plainto_tsquery("simple", q)
            stmt = stmt.where(Ticket.search_vector.op("@@")(tsq))
            count_stmt = count_stmt.where(Ticket.search_vector.op("@@")(tsq))
        else:
            # CRITIQUE: SQLite fallback is ILIKE on title/description.
            # Acceptable for dev with a few thousand rows; never run in
            # production. Switch the engine to Postgres.
            like = f"%{q}%"
            stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
            count_stmt = count_stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))

    return stmt, count_stmt


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


def update_search_vector(ticket: Ticket) -> None:
    """
    summary:
        Refresh the tsvector column for a ticket using the canonical
        weighted format: title (A) + description (B). No-op on
        non-Postgres engines so the dev path stays simple.
    args:
        ticket: Ticket instance to refresh.
    return:
        None.
    """
    if db.engine.dialect.name != "postgresql":
        return
    ticket.search_vector = db.session.execute(
        select(
            func.setweight(func.to_tsvector("simple", func.coalesce(ticket.title, "")), "A").op("||")(
                func.setweight(func.to_tsvector("simple", func.coalesce(ticket.description, "")), "B")
            )
        )
    ).scalar()
