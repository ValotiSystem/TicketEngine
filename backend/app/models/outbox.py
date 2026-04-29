"""
summary:
    Transactional outbox for reliable event emission.

    Pattern: write the event row in the SAME transaction as the
    business state change. A separate worker (`tasks/outbox_drain`)
    drains the table and dispatches the event to the broker. This
    eliminates the "DB committed, broker enqueue lost" failure mode
    of direct enqueue.
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class OutboxEvent(UUIDPk, Timestamps, db.Model):
    __tablename__ = "outbox_events"
    __table_args__ = (
        # Drain query: WHERE dispatched_at IS NULL ORDER BY created_at LIMIT N FOR UPDATE SKIP LOCKED.
        # The partial index keeps it tiny: most rows are dispatched and excluded.
        Index("ix_outbox_pending", "created_at",
              postgresql_where=db.text("dispatched_at IS NULL")),
    )

    tenant_id = tenant_id_column(nullable=True)
    event_type = Column(String(80), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)

    dispatched_at = Column(DateTime(timezone=True))
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(1000))
