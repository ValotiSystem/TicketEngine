"""
summary:
    Idempotency-Key middleware for unsafe HTTP methods.

    When a client sends `Idempotency-Key: <uuid>` on a POST/PATCH/DELETE,
    we store the response (status + body) in Redis keyed by
    (route, key, user). A retry of the same key within TTL replays the
    cached response instead of re-executing. Mirrors Stripe's pattern.

    CRITIQUE: this is best-effort. The strict variant requires a DB row
    insert with UNIQUE(route, key, user) inside the same transaction as
    the business write, otherwise a race between two concurrent retries
    can both pass the check. For high-stakes flows (payments) prefer the
    DB-row variant; for ticket creation this is sufficient.
"""
from __future__ import annotations

import json
import logging
from functools import wraps
from typing import Callable

from flask import request, g, Response

from ..extensions import redis_client

log = logging.getLogger(__name__)

DEFAULT_TTL = 24 * 3600


def idempotent(ttl_seconds: int = DEFAULT_TTL) -> Callable:
    """
    summary:
        Decorator that makes the wrapped view honor the
        `Idempotency-Key` header. If absent, the request flows through
        as normal. If present and a cached response exists, replay it.
        Otherwise execute, then cache the response.
    args:
        ttl_seconds: how long to remember responses keyed by
            Idempotency-Key.
    return:
        Decorator function.
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key_header = request.headers.get("Idempotency-Key")
            if not key_header or redis_client is None:
                return fn(*args, **kwargs)

            uid = getattr(g, "current_user_id", "anon")
            cache_key = f"idem:{request.path}:{uid}:{key_header}"

            try:
                hit = redis_client.get(cache_key)
            except Exception as exc:  # noqa: BLE001
                log.warning("Idempotency read failed: %s", exc)
                hit = None

            if hit:
                payload = json.loads(hit)
                resp = Response(
                    payload["body"],
                    status=payload["status"],
                    mimetype=payload.get("mimetype", "application/json"),
                )
                resp.headers["Idempotent-Replay"] = "true"
                return resp

            result = fn(*args, **kwargs)

            # Normalize the view return into a Response we can cache.
            if isinstance(result, tuple):
                body, status = result[0], result[1] if len(result) > 1 else 200
            else:
                body, status = result, 200
            resp_obj = body if isinstance(body, Response) else Response(
                body.get_data() if hasattr(body, "get_data") else json.dumps(body),
                status=status,
                mimetype="application/json",
            )

            try:
                redis_client.set(
                    cache_key,
                    json.dumps({
                        "status": resp_obj.status_code,
                        "body": resp_obj.get_data(as_text=True),
                        "mimetype": resp_obj.mimetype,
                    }),
                    ex=ttl_seconds,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Idempotency write failed: %s", exc)

            return resp_obj
        return wrapper
    return deco
