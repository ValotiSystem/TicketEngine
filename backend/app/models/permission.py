"""
summary:
    Permission catalogue and Role <-> Permission association.
"""
from sqlalchemy import Column, String, ForeignKey

from ..extensions import db
from .base import UUIDPk, Timestamps


class Permission(UUIDPk, Timestamps, db.Model):
    """
    summary:
        Permissions are global string codes. The Role -> Permission link is
        per-tenant via Role (which is tenant-owned).
    """
    __tablename__ = "permissions"
    code = Column(String(80), unique=True, nullable=False)
    description = Column(String(255))


class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


# Standard permission catalogue. Seeded via fixture.
STANDARD_PERMISSIONS = [
    ("ticket.create",        "Create tickets"),
    ("ticket.read",          "Read tickets within scope"),
    ("ticket.read_all",      "Read every ticket in the tenant"),
    ("ticket.update",        "Update tickets"),
    ("ticket.assign",        "Assign tickets"),
    ("ticket.transition",    "Change ticket status"),
    ("ticket.comment_internal", "Add and read internal comments"),
    ("ticket.close",         "Close tickets"),
    ("ticket.reopen",        "Reopen resolved tickets"),
    ("ticket.reopen_closed", "Reopen closed tickets"),
    ("admin.users",          "Manage users and roles"),
    ("admin.config",         "Configure SLA, queues, categories"),
    ("audit.read",           "Read the audit log"),
]
