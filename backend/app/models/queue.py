"""
summary:
    Queue model. A queue groups tickets for a team or department.
"""
from sqlalchemy import Column, String, UniqueConstraint

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class Queue(UUIDPk, Timestamps, db.Model):
    __tablename__ = "queues"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_queue_tenant_name"),
    )

    tenant_id = tenant_id_column()
    name = Column(String(120), nullable=False)
    description = Column(String(255))
