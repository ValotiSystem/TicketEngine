"""
summary:
    Tenant model. Top-level isolation boundary for the system.
"""
from sqlalchemy import Column, String

from ..extensions import db
from .base import UUIDPk, Timestamps


class Tenant(UUIDPk, Timestamps, db.Model):
    __tablename__ = "tenants"

    name = Column(String(120), nullable=False)
    slug = Column(String(60), unique=True, nullable=False, index=True)

    def __repr__(self):
        return f"<Tenant {self.slug}>"
