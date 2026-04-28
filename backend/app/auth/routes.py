"""
summary:
    Auth blueprint: login, refresh, me, logout.

    CRITIQUE: a real rate limit must live here or in a layer above. Left
    as an explicit TODO.
"""
from __future__ import annotations

from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from ..common.responses import ok
from ..common.decorators import auth_required
from ..schemas.auth import LoginSchema, MeSchema
from ..services import auth_service, audit_service

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    """
    summary:
        Validate credentials and return an access + refresh token pair.
    args:
        none (reads JSON body matching LoginSchema).
    return:
        JSON envelope with access_token and refresh_token.
    """
    data = LoginSchema().load(request.get_json() or {})
    user = auth_service.authenticate(
        email=data["email"],
        password=data["password"],
        tenant_slug=data["tenant_slug"],
    )
    access, refresh = auth_service.make_tokens(user)

    audit_service.record(
        tenant_id=user.tenant_id,
        actor_id=user.id,
        event_type="user.login",
        payload={"ip": request.remote_addr},
    )
    from ..extensions import db
    db.session.commit()

    return ok({"access_token": access, "refresh_token": refresh})


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """
    summary:
        Issue a new access token from a valid refresh token. The refresh
        token itself remains valid until its own expiry.
    args:
        none (refresh JWT carried in Authorization header).
    return:
        JSON envelope with the new access_token.
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    from flask_jwt_extended import create_access_token
    additional = {
        "tenant_id": claims.get("tenant_id"),
        "permissions": claims.get("permissions", []),
        "is_platform_admin": claims.get("is_platform_admin", False),
    }
    access = create_access_token(identity=user_id, additional_claims=additional)
    return ok({"access_token": access})


@bp.get("/me")
@auth_required
def me():
    """
    summary:
        Return the current user profile and effective permissions.
    args:
        none.
    return:
        JSON envelope matching MeSchema.
    """
    from ..extensions import db
    from sqlalchemy import select
    from ..models.user import User
    user = db.session.execute(
        select(User).where(User.id == g.current_user_id, User.tenant_id == g.current_tenant_id)
    ).scalar_one()
    return ok(MeSchema().dump({
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "tenant_id": user.tenant_id,
        "permissions": sorted(g.current_permissions),
    }))


@bp.post("/logout")
@auth_required
def logout():
    """
    summary:
        Record the logout intent. With pure JWT this is best-effort: the
        client must drop its tokens. For real revocation a `jti` blocklist
        in Redis is required.
    args:
        none.
    return:
        JSON envelope with `ok: true`.
    """
    # CRITIQUE: with pure JWT a server-side logout does not exist without
    # a blocklist. For now: the client drops the tokens. For immediate
    # revocation use a revoked-jti store (Redis) and a JWT callback.
    audit_service.record(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        event_type="user.logout",
        payload={},
    )
    from ..extensions import db
    db.session.commit()
    return ok({"ok": True})
