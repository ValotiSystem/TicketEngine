"""
summary:
    Decorators for authentication and authorization.

    Pattern: route handlers are thin and just call services.
    Auth/permission checks live here so they can be reused uniformly.
"""
from __future__ import annotations

from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from .errors import AuthRequired, Forbidden


def auth_required(fn):
    """
    summary:
        Require a valid JWT and populate request-scoped context with
        current user id, tenant id and permission set.
    args:
        fn: route handler being decorated.
    return:
        Wrapped handler that raises AuthRequired/Forbidden when the
        token is missing or lacks tenant context.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            raise AuthRequired() from None
        claims = get_jwt()
        g.current_user_id = get_jwt_identity()
        g.current_tenant_id = claims.get("tenant_id")
        g.current_permissions = set(claims.get("permissions", []))
        if not g.current_tenant_id:
            # CRITIQUE: a token without tenant_id must never be accepted.
            # It would mean the user is "global", and global does not exist
            # here (even the platform admin always acts under a selected
            # tenant).
            raise Forbidden("Token without tenant context")
        return fn(*args, **kwargs)
    return wrapper


def permission_required(*codes: str):
    """
    summary:
        Require ALL of the listed permissions on the current user.
    args:
        codes: permission codes (e.g. "ticket.create", "ticket.assign").
    return:
        Decorator function that raises Forbidden when any required
        permission is missing.
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            missing = [c for c in codes if c not in getattr(g, "current_permissions", set())]
            if missing:
                raise Forbidden(f"Missing permissions: {', '.join(missing)}")
            return fn(*args, **kwargs)
        return wrapper
    return deco
