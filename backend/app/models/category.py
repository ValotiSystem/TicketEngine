"""
summary:
    Hierarchical ticket category.
"""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class TicketCategory(UUIDPk, Timestamps, db.Model):
    __tablename__ = "ticket_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "parent_id", "name", name="uq_cat_tenant_parent_name"),
    )

    tenant_id = tenant_id_column()
    name = Column(String(120), nullable=False)
    parent_id = Column(String(36), ForeignKey("ticket_categories.id", ondelete="RESTRICT"))
