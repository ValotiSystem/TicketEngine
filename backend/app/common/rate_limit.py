"""
summary:
    Redis-backed token-bucket rate limiter exposed as a Flask decorator.

    Algorithm: simple GCRA-style fixed window per (key) using INCR+EXPIRE.
    For brand-new keys we set the TTL on the first request; subsequent
    INCRs share the same window. This trades a bit of accuracy at window
    boundaries for being O(1) and Redis-cheap.

    CRITIQUE: a sliding-window log is more accurate but costs O(N) per
    request. For a fixed-window with strict guarantees use a Lua script
    so INCR + EXPIRE are atomic. Library candidates: redis-py-cluster
    Lua, `limits`, or Cloudflare-style sliding window log.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from flask import g, request

from .errors import RateLimited
from ..extensions import redis_client

log = logging.getLogger(__name__)


def _client_key() -> str:
    """
    summary:
        Build a stable key for the current request, preferring the
        authenticated user id and falling back to the remote address.
    args:
        none.
    return:
        Key string suitable for use as a Redis namespace fragment.
    """
    uid = getattr(g, "current_user_id", None)
    if uid:
        return f"u:{uid}"
    return f"ip:{request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'}"


def rate_limit(scope: str, *, limit: int, window_seconds: int) -> Callable:
    """
    summary:
        Decorator: limit a route to at most `limit` requests per
        `window_seconds` per (scope, client). When Redis is unavailable
        the decorator becomes a no-op (fail-open) and logs a warning.
    args:
        scope: short tag for the protected resource (e.g. "login",
            "ticket_create").
        limit: max number of requests allowed in the window.
        window_seconds: window length in seconds.
    return:
        Decorator function.
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if redis_client is None:
                return fn(*args, **kwargs)
            key = f"rl:{scope}:{_client_key()}"
            try:
                count = redis_client.incr(key)
                if count == 1:
                    redis_client.expire(key, window_seconds)
                if count > limit:
                    raise RateLimited(f"Rate limit exceeded for {scope}")
            except RateLimited:
                raise
            except Exception as exc:  # noqa: BLE001
                # Fail-open: never block legitimate traffic because of cache trouble.
                log.warning("Rate limit check failed (%s): %s", scope, exc)
            return fn(*args, **kwargs)
        return wrapper
    return deco
