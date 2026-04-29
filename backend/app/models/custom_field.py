"""
summary:
    Custom field definitions configurable per tenant from the admin UI.

    A `CustomFieldDefinition` describes ONE additional field that should
    appear on every ticket of a tenant. Field VALUES are stored on the
    ticket itself (in the `custom_fields` JSON column) keyed by the
    definition's `key`. This avoids EAV joins on the hot path.

    CRITIQUE: storing values in JSON keeps reads cheap but makes
    cross-field analytics expensive. When a tenant grows past ~1M
    tickets and starts running BI queries on custom fields, project a
    materialized view per field (or a per-field reporting table) on a
    background job. Do NOT migrate the live store to EAV without a
    measurable need: EAV joins kill latency.
"""
from sqlalchemy import Column, String, Boolean, Integer, JSON, UniqueConstraint, Index

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


# Allowed field types. Adding a new type means:
#   1. Append it here
#   2. Teach `validate_value` in services/custom_field_service.py
#   3. Render it in the frontend CustomFieldsForm component
ALLOWED_TYPES = ("text", "longtext", "number", "bool", "date", "select", "multiselect", "url", "email")


class CustomFieldDefinition(UUIDPk, Timestamps, db.Model):
    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_custom_field_tenant_key"),
        Index("ix_custom_field_tenant_active_order", "tenant_id", "is_active", "display_order"),
    )

    tenant_id = tenant_id_column()

    # Stable machine key used as the JSON property name on tickets.
    # Lowercase, underscore-separated; never change after creation
    # (would orphan existing values).
    key = Column(String(60), nullable=False)
    label = Column(String(160), nullable=False)
    field_type = Column(String(20), nullable=False)
    is_required = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)

    # Free-form per-type config. For select/multiselect: {"options": ["a","b"]}.
    # For number: {"min": 0, "max": 100}. For text: {"max_length": 255, "regex": "..."}.
    config = Column(JSON, nullable=False, default=dict)
    help_text = Column(String(500))
