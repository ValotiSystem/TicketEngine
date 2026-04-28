"""
summary:
    Tag model and Ticket <-> Tag association.
"""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class Tag(UUIDPk, Timestamps, db.Model):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tag_tenant_name"),
    )

    tenant_id = tenant_id_column()
    name = Column(String(60), nullable=False)


class TicketTag(db.Model):
    __tablename__ = "ticket_tags"
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
