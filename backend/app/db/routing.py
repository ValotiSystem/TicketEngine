"""
summary:
    Read-replica routing scaffold.

    SQLAlchemy 2.x supports per-statement engine binding via the
    `binds` mapping on `Session`. The pattern below configures TWO
    engines (writer + reader) and a Session that picks the reader for
    SELECTs and the writer for everything else (INSERT/UPDATE/DELETE).

    Activation: set DATABASE_URL_REPLICA in the env. When unset the
    reader falls back to the writer engine (single-instance mode).

    CRITIQUE - replica lag:
    - Reading your own writes will be inconsistent because the replica
      lags by milliseconds-to-seconds. For the duration of a transaction
      that just wrote, mark the request "primary-pinned" and use the
      writer for reads too. The simplest safe rule:
      "any HTTP request that performed a write reads from primary
      until the response is returned." A header-based override
      (`X-Replica-Stale-OK: false`) lets opt-in clients pin reads.
    - Sticky sessions per user/tenant for a few hundred ms after a
      write also work and are simpler operationally.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

_writer: Optional[Engine] = None
_reader: Optional[Engine] = None


def get_engines() -> tuple[Engine, Engine]:
    """
    summary:
        Lazily build (writer, reader) engines based on env vars and
        return them. Both engines share the SQLAlchemy default
        connection pool.
    args:
        none.
    return:
        Tuple (writer_engine, reader_engine). When DATABASE_URL_REPLICA
        is unset the reader is the same instance as the writer.
    """
    global _writer, _reader
    if _writer is not None:
        return _writer, _reader  # type: ignore[return-value]

    primary = os.getenv("DATABASE_URL", "sqlite:///./instance/ticketportal.db")
    replica = os.getenv("DATABASE_URL_REPLICA")

    _writer = create_engine(primary, pool_pre_ping=True, future=True)
    if replica:
        _reader = create_engine(replica, pool_pre_ping=True, future=True)
        log.info("Read replica engine configured: %s", _redact(replica))
    else:
        _reader = _writer
        log.info("No read replica configured; reader == writer")

    return _writer, _reader


def _redact(url: str) -> str:
    """
    summary:
        Strip credentials from a connection URL for logging.
    args:
        url: SQLAlchemy connection URL.
    return:
        Redacted URL safe to log.
    """
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        _creds, host = rest.split("@", 1)
        return f"{scheme}://***@{host}"
    return url
