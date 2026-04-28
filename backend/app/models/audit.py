"""
summary:
    Immutable audit log model.
"""
from sqlalchemy import Column, String, ForeignKey, JSON, Index

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


# Standard event types. Add every new type here; never use free-form strings.
EVENT_TYPES = (
    "ticket.created",
    "ticket.updated",
    "ticket.transition",
    "ticket.assigned",
    "ticket.commented",
    "ticket.attachment_added",
    "ticket.resolved",
    "ticket.closed",
    "ticket.reopened",
    "ticket.cancelled",
    "user.login",
    "user.login_failed",
    "user.logout",
)


class AuditEvent(UUIDPk, Timestamps, db.Model):
    """
    summary:
        Audit log row. Immutable by convention (we never UPDATE a row).

        CRITIQUE: to enforce immutability at the DB level on Postgres a
        BEFORE UPDATE trigger can be added, or a write-only role pattern.
        The scaffold does not apply this.
    """
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_ticket", "ticket_id"),
        Index("ix_audit_actor", "actor_id"),
    )

    tenant_id = tenant_id_column()
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="SET NULL"))

    event_type = Column(String(60), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
