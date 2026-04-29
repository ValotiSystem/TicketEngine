"""
summary:
    Admin blueprint: tenant configuration. Currently exposes the
    custom-field definitions CRUD. New admin sub-resources should land
    here behind the `admin.config` permission.
"""
from __future__ import annotations

from flask import Blueprint, request, g

from ..common.decorators import auth_required, permission_required
from ..common.responses import ok
from ..schemas.custom_field import (
    CustomFieldCreateSchema, CustomFieldUpdateSchema, CustomFieldOutSchema,
)
from ..services import custom_field_service as cfs
from ..repositories import custom_field_repository as cfr

bp = Blueprint("admin", __name__)


@bp.get("/custom-fields")
@auth_required
@permission_required("admin.config")
def list_custom_fields():
    """
    summary:
        Return every custom field definition for the current tenant
        (active and inactive) ordered for the admin UI.
    args:
        none.
    return:
        JSON envelope with a list of CustomFieldOutSchema items.
    """
    items = cfr.list_all(g.current_tenant_id)
    return ok(CustomFieldOutSchema().dump(items, many=True))


@bp.post("/custom-fields")
@auth_required
@permission_required("admin.config")
def create_custom_field():
    """
    summary:
        Create a new custom field definition.
    args:
        none (reads JSON body matching CustomFieldCreateSchema).
    return:
        JSON envelope with the created CustomFieldOutSchema, HTTP 201.
    """
    data = CustomFieldCreateSchema().load(request.get_json() or {})
    cf = cfs.create(tenant_id=g.current_tenant_id, actor_id=g.current_user_id, **data)
    return ok(CustomFieldOutSchema().dump(cf)), 201


@bp.patch("/custom-fields/<field_id>")
@auth_required
@permission_required("admin.config")
def update_custom_field(field_id: str):
    """
    summary:
        Patch an existing custom field definition.
    args:
        field_id: id of the definition.
    return:
        JSON envelope with the updated CustomFieldOutSchema.
    """
    patch = CustomFieldUpdateSchema().load(request.get_json() or {}, partial=True)
    cf = cfs.update(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        field_id=field_id,
        patch=patch,
    )
    return ok(CustomFieldOutSchema().dump(cf))


@bp.delete("/custom-fields/<field_id>")
@auth_required
@permission_required("admin.config")
def deactivate_custom_field(field_id: str):
    """
    summary:
        Deactivate (soft-delete) a custom field definition. Existing
        ticket values are preserved on disk and excluded from new forms.
    args:
        field_id: id of the definition.
    return:
        JSON envelope with the updated CustomFieldOutSchema.
    """
    cf = cfs.deactivate(
        tenant_id=g.current_tenant_id,
        actor_id=g.current_user_id,
        field_id=field_id,
    )
    return ok(CustomFieldOutSchema().dump(cf))
