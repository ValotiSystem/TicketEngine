"""
summary:
    SLA policy: simple first-response and resolve targets.
"""
from sqlalchemy import Column, String, Integer, UniqueConstraint

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class SLAPolicy(UUIDPk, Timestamps, db.Model):
    """
    summary:
        Minimal SLA policy: first response and resolve minutes.

        CRITIQUE: a realistic SLA needs rules per priority + category +
        business hours + holidays. The schema is intentionally flat;
        extend it during Phase 2.
    """
    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_sla_tenant_name"),
    )

    tenant_id = tenant_id_column()
    name = Column(String(120), nullable=False)
    first_response_minutes = Column(Integer, nullable=False, default=240)
    resolve_minutes = Column(Integer, nullable=False, default=2880)
