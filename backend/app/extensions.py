"""
summary:
    Flask extensions instantiated centrally to avoid circular imports.

    `redis_client` is a module-level singleton initialized lazily by
    `init_redis(app)` from the application factory. Code that uses
    Redis (cache, rate limiting, idempotency) imports the symbol and
    treats `None` as "Redis disabled / unreachable" without crashing.
"""
import logging
import os
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

log = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Redis is optional in dev. Initialized by init_redis() from create_app().
redis_client = None  # type: Optional["redis.Redis"]


def init_redis(app):
    """
    summary:
        Build a Redis client from REDIS_URL and store it as a
        module-level singleton. Failures during ping log a warning but
        never raise: every Redis-dependent feature must fail-open.
    args:
        app: Flask application.
    return:
        None.
    """
    global redis_client
    url = app.config.get("REDIS_URL") or os.getenv("REDIS_URL")
    if not url:
        log.info("REDIS_URL not set; Redis-backed features disabled")
        return
    try:
        import redis  # type: ignore
        client = redis.Redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
        client.ping()
        redis_client = client
        log.info("Redis connected")
    except Exception as exc:  # noqa: BLE001
        log.warning("Redis init failed (features will fail-open): %s", exc)
        redis_client = None
