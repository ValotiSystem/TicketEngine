"""
summary:
    Tenant-aware data access for custom field definitions.
"""
from __future__ import annotations

from sqlalchemy import select

from ..extensions import db
from ..models.custom_field import CustomFieldDefinition
from ..common.errors import NotFound


def list_active(tenant_id: str) -> list[CustomFieldDefinition]:
    """
    summary:
        Return active custom field definitions for a tenant in display
        order.
    args:
        tenant_id: tenant scope.
    return:
        Ordered list of CustomFieldDefinition instances.
    """
    return list(db.session.execute(
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.tenant_id == tenant_id, CustomFieldDefinition.is_active.is_(True))
        .order_by(CustomFieldDefinition.display_order.asc(), CustomFieldDefinition.created_at.asc())
    ).scalars())


def list_all(tenant_id: str) -> list[CustomFieldDefinition]:
    """
    summary:
        Return every custom field definition for a tenant (including
        inactive) in display order. For the admin UI.
    args:
        tenant_id: tenant scope.
    return:
        Ordered list of CustomFieldDefinition instances.
    """
    return list(db.session.execute(
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.tenant_id == tenant_id)
        .order_by(CustomFieldDefinition.display_order.asc(), CustomFieldDefinition.created_at.asc())
    ).scalars())


def get(tenant_id: str, field_id: str) -> CustomFieldDefinition:
    """
    summary:
        Fetch a single custom field definition by id, scoped to tenant.
    args:
        tenant_id: tenant scope.
        field_id: custom field definition id.
    return:
        CustomFieldDefinition instance.
    """
    cf = db.session.execute(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.tenant_id == tenant_id,
            CustomFieldDefinition.id == field_id,
        )
    ).scalar_one_or_none()
    if not cf:
        raise NotFound("Custom field not found")
    return cf
