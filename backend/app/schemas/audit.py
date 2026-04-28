"""
summary:
    Marshmallow schema for audit event responses.
"""
from marshmallow import Schema, fields


class AuditEventOutSchema(Schema):
    id = fields.String()
    actor_id = fields.String(allow_none=True)
    ticket_id = fields.String(allow_none=True)
    event_type = fields.String()
    payload = fields.Dict()
    created_at = fields.DateTime()
