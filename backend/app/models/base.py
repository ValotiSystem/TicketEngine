"""
summary:
    Reusable model mixins: UUID primary key, timestamps, tenant_id helper.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from ..extensions import db


def _utcnow():
    """
    summary:
        Return the current UTC datetime (timezone-aware).
    args:
        none.
    return:
        datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class UUIDPk:
    # CRITIQUE: stored as a string for sqlite/postgres portability without
    # dialect-specific types. In a Postgres-only deployment switch to native
    # PGUUID for slightly smaller storage and faster comparisons.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class Timestamps:
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class TenantOwned:
    """
    summary:
        Marker mixin for multi-tenant business tables.

        Golden rule: every query must filter by tenant_id. The repository
        layer enforces this invariant. See `app/repositories/`.
    """
    @classmethod
    def __declare_last__(cls):
        # placeholder for runtime constraints
        pass


def tenant_id_column(nullable: bool = False):
    """
    summary:
        Build a standardized tenant_id foreign key column.
    args:
        nullable: whether the column is nullable (default False).
    return:
        SQLAlchemy Column ready to be assigned on a model.
    """
    return Column(String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=nullable, index=True)
