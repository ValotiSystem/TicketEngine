"""
summary:
    Marshmallow schemas for the auth blueprint.
"""
from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    tenant_slug = fields.String(required=True, validate=validate.Length(min=1, max=60))
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=1))


class TokenPairSchema(Schema):
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)


class MeSchema(Schema):
    id = fields.String()
    email = fields.Email()
    full_name = fields.String()
    tenant_id = fields.String()
    permissions = fields.List(fields.String())
