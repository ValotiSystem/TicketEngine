"""
summary:
    Tickets blueprint. Thin route handlers: each is 5-10 lines.
"""
from __future__ import annotations

from flask import Blueprint, request, g
from sqlalchemy import select

from ..common.decorators import auth_required, permission_required
from ..common.responses import ok, paginated
from ..schemas.ticket import (
    TicketCreateSchema, TicketUpdateSchema, TicketTransitionSchema,
    TicketAssignSchema, TicketOutSchema,
    CommentCreateSchema, CommentOutSchema,
)
from ..services import ticket_service
from ..repositories import ticket_repository as tr
from ..extensions import db
from ..models.comment import Comment

bp = Blueprint("tickets", __name__)


@bp.get("")
@auth_required
@permission_required("ticket.read")
def list_tickets():
    """
    summary:
        Return a paginated, filtered list of tickets for the current
        tenant.
    args:
        none (filters carried as query string parameters).
    return:
        Paginated JSON response of TicketOutSchema items.
    """
    args = request.args
    items, total = tr.list_tickets(
        tenant_id=g.current_tenant_id,
        page=int(args.get("page", 1)),
        page_size=int(args.get("page_size", 25)),
        status=args.get("status"),
        assignee_id=args.get("assignee_id"),
        queue_id=args.get("queue_id"),
        requester_id=args.get("requester_id"),
        q=args.get("q"),
        sort=args.get("sort", "-created_at"),
    )
    return paginated(items, total, TicketOutSchema())


@bp.post("")
@auth_required
@permission_required("ticket.create")
def create_ticket():
    """
    summary:
        Create a new ticket on behalf of the current user.
    args:
        none (reads JSON body matching TicketCreateSchema).
    return:
        JSON envelope of the created TicketOutSchema, HTTP 201.
    """
    data = TicketCreateSchema().load(request.get_json() or {})
    ticket = ticket_service.create_ticket(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        **data,
    )
    return ok(TicketOutSchema().dump(ticket)), 201


@bp.get("/<ticket_id>")
@auth_required
@permission_required("ticket.read")
def get_ticket(ticket_id):
    """
    summary:
        Return a single ticket by id.
    args:
        ticket_id: id of the ticket to fetch.
    return:
        JSON envelope of TicketOutSchema.
    """
    t = tr.get_by_id(g.current_tenant_id, ticket_id)
    return ok(TicketOutSchema().dump(t))


@bp.patch("/<ticket_id>")
@auth_required
@permission_required("ticket.update")
def update_ticket(ticket_id):
    """
    summary:
        Apply a partial update to a ticket's editable fields.
    args:
        ticket_id: id of the ticket to update.
    return:
        JSON envelope of the updated TicketOutSchema.
    """
    data = TicketUpdateSchema().load(request.get_json() or {}, partial=True)
    t = tr.get_by_id(g.current_tenant_id, ticket_id)
    for k, v in data.items():
        setattr(t, k, v)
    db.session.commit()
    return ok(TicketOutSchema().dump(t))


@bp.post("/<ticket_id>/comments")
@auth_required
@permission_required("ticket.read")
def add_comment(ticket_id):
    """
    summary:
        Append a comment to a ticket.
    args:
        ticket_id: id of the target ticket.
    return:
        JSON envelope of the created CommentOutSchema, HTTP 201.
    """
    data = CommentCreateSchema().load(request.get_json() or {})
    c = ticket_service.add_comment(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        ticket_id=ticket_id,
        body=data["body"],
        is_internal=data["is_internal"],
        actor_permissions=g.current_permissions,
    )
    return ok(CommentOutSchema().dump(c)), 201


@bp.get("/<ticket_id>/comments")
@auth_required
@permission_required("ticket.read")
def list_comments(ticket_id):
    """
    summary:
        List comments on a ticket. Internal comments are filtered out
        when the requester lacks the `ticket.comment_internal` permission.
    args:
        ticket_id: id of the target ticket.
    return:
        JSON envelope with a list of CommentOutSchema items.
    """
    tr.get_by_id(g.current_tenant_id, ticket_id)  # tenant + existence check

    stmt = select(Comment).where(
        Comment.tenant_id == g.current_tenant_id,
        Comment.ticket_id == ticket_id,
    ).order_by(Comment.created_at.asc())

    if "ticket.comment_internal" not in g.current_permissions:
        stmt = stmt.where(Comment.is_internal.is_(False))

    items = db.session.execute(stmt).scalars().all()
    return ok(CommentOutSchema().dump(items, many=True))


@bp.post("/<ticket_id>/assign")
@auth_required
@permission_required("ticket.assign")
def assign(ticket_id):
    """
    summary:
        Set or clear the assignee of a ticket.
    args:
        ticket_id: id of the target ticket.
    return:
        JSON envelope of the updated TicketOutSchema.
    """
    data = TicketAssignSchema().load(request.get_json() or {})
    t = ticket_service.assign(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        ticket_id=ticket_id,
        assignee_id=data.get("assignee_id"),
    )
    return ok(TicketOutSchema().dump(t))


@bp.post("/<ticket_id>/transition")
@auth_required
@permission_required("ticket.transition")
def transition(ticket_id):
    """
    summary:
        Move a ticket to a new status, applying state-machine and
        permission checks.
    args:
        ticket_id: id of the target ticket.
    return:
        JSON envelope of the updated TicketOutSchema.
    """
    data = TicketTransitionSchema().load(request.get_json() or {})
    t = ticket_service.transition(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        ticket_id=ticket_id,
        to_status=data["to_status"],
        reason=data.get("reason"),
        actor_permissions=g.current_permissions,
    )
    return ok(TicketOutSchema().dump(t))
