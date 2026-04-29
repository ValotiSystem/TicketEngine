"""
summary:
    Transactional outbox helpers.

    Producer side: `enqueue` adds an OutboxEvent to the current session
    (the caller commits as part of the business transaction).
    Consumer side: `drain_batch` is invoked by the Celery beat task in
    `tasks/outbox_drain.py`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update

from ..extensions import db
from ..models.outbox import OutboxEvent

log = logging.getLogger(__name__)

DRAIN_BATCH = 100
MAX_ATTEMPTS = 10


def enqueue(*, event_type: str, payload: dict[str, Any], tenant_id: Optional[str] = None) -> OutboxEvent:
    """
    summary:
        Stage an outbox event on the current SQLAlchemy session. The
        caller is responsible for committing within the same transaction
        as the business state change.
    args:
        event_type: dotted event type (e.g. "ticket.created").
        payload: JSON-serializable event body.
        tenant_id: optional tenant scope (None for system events).
    return:
        The staged OutboxEvent instance.
    """
    evt = OutboxEvent(tenant_id=tenant_id, event_type=event_type, payload=payload)
    db.session.add(evt)
    return evt


def drain_batch(dispatch) -> int:
    """
    summary:
        Pull up to DRAIN_BATCH undispatched events with row locks
        (FOR UPDATE SKIP LOCKED on Postgres) and hand each one to the
        `dispatch` callable. Marks delivered events as dispatched in the
        same transaction; on dispatch errors increments attempts and
        records the last error string. Multiple workers can run in
        parallel safely thanks to SKIP LOCKED.
    args:
        dispatch: callable(event_type: str, payload: dict, tenant_id) ->
            None. Must raise on permanent failure if you want backoff;
            transient failures should also raise to trigger retry.
    return:
        Number of events processed in this batch (delivered or failed).
    """
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.dispatched_at.is_(None), OutboxEvent.attempts < MAX_ATTEMPTS)
        .order_by(OutboxEvent.created_at.asc())
        .limit(DRAIN_BATCH)
        .with_for_update(skip_locked=True)
    )
    rows = list(db.session.execute(stmt).scalars())
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    delivered_ids: list[str] = []
    failed: list[tuple[str, str]] = []

    for evt in rows:
        try:
            dispatch(evt.event_type, evt.payload, evt.tenant_id)
            delivered_ids.append(evt.id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Outbox dispatch failed: %s", evt.event_type)
            failed.append((evt.id, str(exc)[:1000]))

    if delivered_ids:
        db.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id.in_(delivered_ids))
            .values(dispatched_at=now)
        )
    for evt_id, err in failed:
        db.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == evt_id)
            .values(attempts=OutboxEvent.attempts + 1, last_error=err)
        )

    db.session.commit()
    return len(rows)
