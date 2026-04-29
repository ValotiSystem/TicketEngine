"""
summary:
    Tiny Redis cache wrapper. Designed to be a HARD dependency only when
    actually used: if Redis is unreachable, callers fall back to the
    expensive computation. Failure of the cache must never break the
    request path.

    CRITIQUE: a real production cache also needs:
    - per-key TTL randomization to avoid stampedes
    - circuit breaker so repeated failures stop hammering Redis
    - metrics for hit/miss ratio per cache namespace
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from ..extensions import redis_client

log = logging.getLogger(__name__)


def get_or_set(key: str, ttl_seconds: int, producer: Callable[[], Any]) -> Any:
    """
    summary:
        Return the cached JSON value at `key`. On cache miss or any
        Redis error, run `producer()`, cache the result for `ttl_seconds`
        (best effort) and return it.
    args:
        key: Redis key (callers MUST namespace, e.g. "perm:<user_id>").
        ttl_seconds: cache TTL in seconds.
        producer: zero-arg function that recomputes the value on miss.
    return:
        The cached or freshly produced value.
    """
    if redis_client is None:
        return producer()

    try:
        raw = redis_client.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache read failed (%s): %s", key, exc)

    value = producer()
    try:
        redis_client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache write failed (%s): %s", key, exc)
    return value


def invalidate(key: str) -> None:
    """
    summary:
        Best-effort delete of a cache key.
    args:
        key: Redis key.
    return:
        None.
    """
    if redis_client is None:
        return
    try:
        redis_client.delete(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache invalidate failed (%s): %s", key, exc)


def invalidate_prefix(prefix: str, *, batch: int = 500) -> None:
    """
    summary:
        Best-effort delete of every key matching `prefix*` using SCAN to
        avoid blocking Redis (KEYS is forbidden in production).
    args:
        prefix: key prefix to invalidate.
        batch: SCAN COUNT hint.
    return:
        None.
    """
    if redis_client is None:
        return
    try:
        for k in redis_client.scan_iter(match=f"{prefix}*", count=batch):
            redis_client.delete(k)
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache prefix invalidate failed (%s): %s", prefix, exc)
