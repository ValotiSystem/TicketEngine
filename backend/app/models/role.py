"""
summary:
    Role and User<->Role association.
"""
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class Role(UUIDPk, Timestamps, db.Model):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    tenant_id = tenant_id_column()
    name = Column(String(80), nullable=False)


class UserRole(db.Model):
    """
    summary:
        Association table users <-> roles.

        CRITIQUE: a user's effective permissions are the cartesian product
        of all their role permissions, computed at runtime. For performance
        a materialized view or a short-TTL Redis cache can be added.
    """
    __tablename__ = "user_roles"
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
