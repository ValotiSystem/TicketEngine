"""
summary:
    Authentication and authorization service.

    CRITIQUE - JWT vs sessions:
    The original spec mentioned both. The scaffold uses JWT (access +
    refresh) because:
    - SPA cross-origin: less friction than cookie sessions + CSRF
    - stateless on the backend: scales horizontally
    Trade-off: revocation is awkward. Mitigation: short-lived refresh
    tokens (7 days default) and a Redis `jti` blocklist when immediate
    revocation is required.
"""
from __future__ import annotations

from typing import Optional

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import select

from ..extensions import db
from ..models.user import User
from ..models.role import UserRole, Role
from ..models.permission import RolePermission, Permission
from ..common.errors import AuthRequired, ValidationError


def authenticate(email: str, password: str, tenant_slug: str) -> User:
    """
    summary:
        Verify a tenant + email + password tuple and return the matching
        active user.
    args:
        email: user email.
        password: plaintext password.
        tenant_slug: tenant short identifier (URL-safe).
    return:
        User instance on success.
    """
    # CRITIQUE: a login rate limit must live at the middleware/gateway
    # level, not here. Left as an explicit TODO.
    if not email or not password or not tenant_slug:
        raise ValidationError("Missing credentials")

    from ..models.tenant import Tenant
    tenant = db.session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    ).scalar_one_or_none()
    if not tenant:
        # Same message as a password fail so the existence of the tenant
        # is not leaked to the caller.
        raise AuthRequired("Invalid credentials")

    user = db.session.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email)
    ).scalar_one_or_none()
    if not user or not user.is_active or not user.check_password(password):
        raise AuthRequired("Invalid credentials")

    return user


def get_user_permissions(user_id: str) -> set[str]:
    """
    summary:
        Compute the set of effective permission codes for a user.
    args:
        user_id: id of the user.
    return:
        Set of permission code strings.
    """
    rows = db.session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    ).all()
    return {r[0] for r in rows}


def make_tokens(user: User) -> tuple[str, str]:
    """
    summary:
        Build an access + refresh JWT pair for the given user.
    args:
        user: User instance the tokens are issued for.
    return:
        Tuple (access_token, refresh_token).
    """
    perms = sorted(get_user_permissions(user.id))
    additional = {
        "tenant_id": user.tenant_id,
        "permissions": perms,
        "is_platform_admin": user.is_platform_admin,
    }
    access = create_access_token(identity=user.id, additional_claims=additional)
    refresh = create_refresh_token(identity=user.id, additional_claims=additional)
    return access, refresh
