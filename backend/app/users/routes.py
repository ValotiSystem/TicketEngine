"""
summary:
    Users blueprint (admin). Stub: list only for now.
"""
from __future__ import annotations

from flask import Blueprint, g
from sqlalchemy import select

from ..common.decorators import auth_required, permission_required
from ..common.responses import ok
from ..extensions import db
from ..models.user import User

bp = Blueprint("users", __name__)


@bp.get("")
@auth_required
@permission_required("admin.users")
def list_users():
    """
    summary:
        Return all users in the current tenant.
    args:
        none.
    return:
        JSON envelope with a list of user dicts.
    """
    items = db.session.execute(
        select(User).where(User.tenant_id == g.current_tenant_id)
    ).scalars().all()
    return ok([
        {"id": u.id, "email": u.email, "full_name": u.full_name, "is_active": u.is_active}
        for u in items
    ])
