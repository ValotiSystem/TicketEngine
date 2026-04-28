"""
summary:
    Audit blueprint: read-only listing of audit events.
"""
from __future__ import annotations

from flask import Blueprint, request, g
from sqlalchemy import select, func

from ..common.decorators import auth_required, permission_required
from ..common.responses import paginated
from ..extensions import db
from ..models.audit import AuditEvent
from ..schemas.audit import AuditEventOutSchema

bp = Blueprint("audit", __name__)


@bp.get("")
@auth_required
@permission_required("audit.read")
def list_events():
    """
    summary:
        Return a paginated, filtered list of audit events for the
        current tenant.
    args:
        none (filters carried as query string parameters: ticket_id,
            event_type, page, page_size).
    return:
        Paginated JSON response of AuditEventOutSchema items.
    """
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 50)), 200)

    base = select(AuditEvent).where(AuditEvent.tenant_id == g.current_tenant_id)
    count_stmt = select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == g.current_tenant_id)

    if ticket_id := request.args.get("ticket_id"):
        base = base.where(AuditEvent.ticket_id == ticket_id)
        count_stmt = count_stmt.where(AuditEvent.ticket_id == ticket_id)
    if event_type := request.args.get("event_type"):
        base = base.where(AuditEvent.event_type == event_type)
        count_stmt = count_stmt.where(AuditEvent.event_type == event_type)

    base = base.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    items = db.session.execute(base).scalars().all()
    total = db.session.execute(count_stmt).scalar_one()
    return paginated(items, total, AuditEventOutSchema())
