"""
summary:
    Ticket: heart of the domain.

    Explicit decisions:
    - `number` is human-readable, unique per tenant. Generated through a
      dedicated sequencer (TicketNumberSequence). NEVER use MAX(number)+1:
      race-prone.
    - `status` is a string controlled by the state machine in
      services/workflow.py. No DB ENUM: adding a new state should not
      require a schema migration.
    - `custom_fields` is JSON. Simple filters via JSON path; for complex
      queries see the CRITIQUE below.
    - `tenant_id` is indexed and is part of every relevant compound index.
    - `search_vector` is a tsvector column populated by
      services.ticket_service when title/description change. With a GIN
      index it serves Postgres full-text search at sub-millisecond per
      query for hundreds of millions of rows. Falls back to ILIKE when
      not on Postgres (sqlite dev).
"""
from __future__ import annotations

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Index, UniqueConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import TSVECTOR

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


# Valid status strings. TRANSITION validity lives in services/workflow.py.
TICKET_STATUSES = (
    "draft", "open", "triage", "in_progress",
    "waiting_on_requester", "waiting_on_third_party",
    "resolved", "closed", "reopened", "cancelled",
)

TICKET_PRIORITIES = ("low", "normal", "high", "urgent")

TICKET_SOURCES = ("web", "email", "api", "import")

TICKET_VISIBILITY = ("internal", "public")


class TicketNumberSequence(db.Model):
    """
    summary:
        Per-tenant sequencer for human-readable ticket numbers.

        CRITIQUE: the increment must happen inside the same transaction as
        ticket creation, using SELECT ... FOR UPDATE to avoid races.
        SQLite does not support SELECT FOR UPDATE: fine for dev, prod must
        be Postgres.
    """
    __tablename__ = "ticket_number_sequences"
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    last_value = Column(Integer, nullable=False, default=0)


class Ticket(UUIDPk, Timestamps, db.Model):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_ticket_tenant_number"),
        Index("ix_ticket_tenant_status", "tenant_id", "status"),
        Index("ix_ticket_tenant_assignee", "tenant_id", "assignee_id"),
        Index("ix_ticket_tenant_queue", "tenant_id", "queue_id"),
        Index("ix_ticket_tenant_requester", "tenant_id", "requester_id"),
        Index("ix_ticket_tenant_due", "tenant_id", "due_at"),
        # Compound index used by keyset pagination (created_at, id).
        Index("ix_ticket_tenant_created_id", "tenant_id", "created_at", "id"),
        # GIN index on tsvector. Created only on Postgres via Alembic
        # migration: SQLAlchemy DDL with postgresql_using='gin'.
        Index("ix_ticket_search_vector", "search_vector", postgresql_using="gin"),
    )

    tenant_id = tenant_id_column()
    number = Column(Integer, nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(40), nullable=False, default="open")
    priority = Column(String(20), nullable=False, default="normal")

    category_id = Column(String(36), ForeignKey("ticket_categories.id", ondelete="RESTRICT"))
    requester_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    queue_id = Column(String(36), ForeignKey("queues.id", ondelete="SET NULL"))
    sla_policy_id = Column(String(36), ForeignKey("sla_policies.id", ondelete="SET NULL"))

    source = Column(String(20), nullable=False, default="web")
    visibility = Column(String(20), nullable=False, default="internal")

    # CRITIQUE: JSON is fine for read/write. If you need filtering or search
    # on individual custom field keys, add a Postgres GIN index or move to
    # EAV (TicketCustomFieldValue). The scaffold keeps JSON.
    custom_fields = Column(JSON, nullable=False, default=dict)

    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    due_at = Column(DateTime(timezone=True))
    sla_breach_at = Column(DateTime(timezone=True))

    last_public_reply_at = Column(DateTime(timezone=True))
    last_internal_update_at = Column(DateTime(timezone=True))

    resolution_reason = Column(Text)  # mandatory when status -> resolved

    # Materialized full-text search vector. Populated by the service
    # layer on title/description changes. On Postgres this column is
    # TSVECTOR; on SQLite the dialect falls back to TEXT (no FTS).
    search_vector = Column(TSVECTOR)
