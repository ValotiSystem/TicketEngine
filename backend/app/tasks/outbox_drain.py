"""
summary:
    Periodic Celery task that drains the outbox table.

    Scheduled by celery beat (see tasks/__init__.py beat_schedule).
    Designed to be safe to run on multiple worker processes
    simultaneously: SELECT ... FOR UPDATE SKIP LOCKED makes the drain
    horizontally scalable across N workers.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from . import celery_app
from .notifications import notify_event

log = logging.getLogger(__name__)


def _dispatch(event_type: str, payload: dict[str, Any], tenant_id: Optional[str]) -> None:
    """
    summary:
        Route an outbox event to the appropriate downstream task. New
        event types should be added to this dispatch table.
    args:
        event_type: dotted event type.
        payload: event body.
        tenant_id: optional tenant scope.
    return:
        None. Raises on transient failures so the outbox row remains
        undispatched and is retried on the next drain.
    """
    if event_type.startswith("ticket."):
        ticket_id = payload.get("ticket_id")
        notify_event.delay(event_type, ticket_id)
        return
    log.warning("Outbox event with no dispatcher: %s", event_type)


@celery_app.task(name="outbox.drain")
def drain():
    """
    summary:
        Drain a batch of outbox events. Runs inside the Flask app
        context so SQLAlchemy can use the configured database engine.
    args:
        none.
    return:
        Number of events processed in this run.
    """
    from app import create_app
    from app.services.outbox import drain_batch

    app = create_app()
    with app.app_context():
        n = drain_batch(_dispatch)
        if n:
            log.info("Outbox drained %d events", n)
        return n
