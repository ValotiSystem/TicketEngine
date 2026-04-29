"""
summary:
    Marshmallow schemas for custom field admin endpoints.
"""
from marshmallow import Schema, fields, validate

from ..models.custom_field import ALLOWED_TYPES


class CustomFieldCreateSchema(Schema):
    key = fields.String(required=True, validate=validate.Length(min=1, max=60))
    label = fields.String(required=True, validate=validate.Length(min=1, max=160))
    field_type = fields.String(required=True, validate=validate.OneOf(ALLOWED_TYPES))
    is_required = fields.Boolean(load_default=False)
    is_active = fields.Boolean(load_default=True)
    display_order = fields.Integer(load_default=0)
    config = fields.Dict(load_default=dict)
    help_text = fields.String(load_default=None, allow_none=True)


class CustomFieldUpdateSchema(Schema):
    label = fields.String(validate=validate.Length(min=1, max=160))
    is_required = fields.Boolean()
    is_active = fields.Boolean()
    display_order = fields.Integer()
    config = fields.Dict()
    help_text = fields.String(allow_none=True)


class CustomFieldOutSchema(Schema):
    id = fields.String()
    key = fields.String()
    label = fields.String()
    field_type = fields.String()
    is_required = fields.Boolean()
    is_active = fields.Boolean()
    display_order = fields.Integer()
    config = fields.Dict()
    help_text = fields.String(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
