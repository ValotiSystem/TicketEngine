"""
summary:
    Async notifications.

    CRITIQUE: this is a stub. A real notification system needs:
    - multi-channel (email, in-app, webhook)
    - idempotent (dedup key = (event_type, ticket_id, version))
    - retry with exponential backoff (autoretry_for in the Celery
      decorator)
    - dead-letter queue after N retries
    - per-user preferences: who wants notifications about what
"""
from __future__ import annotations

import logging

from . import celery_app

log = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    name="notify_event",
)
def notify_event(self, event_type: str, ticket_id: str):
    """
    summary:
        Send notifications for a given ticket-related event.
        Currently a stub that logs the event.
    args:
        event_type: notification type (e.g. "ticket.created").
        ticket_id: id of the related ticket.
    return:
        Dict with the event details.
    """
    log.info("notify_event %s for ticket=%s (stub)", event_type, ticket_id)
    # TODO Phase 2: render template + send SMTP + webhook
    return {"event": event_type, "ticket_id": ticket_id}
