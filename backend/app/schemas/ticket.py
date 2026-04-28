"""
summary:
    Marshmallow schemas for ticket-related endpoints.
"""
from marshmallow import Schema, fields, validate

from ..models.ticket import TICKET_STATUSES, TICKET_PRIORITIES


class TicketCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=True, validate=validate.Length(min=1))
    priority = fields.String(load_default="normal", validate=validate.OneOf(TICKET_PRIORITIES))
    category_id = fields.String(load_default=None)
    queue_id = fields.String(load_default=None)
    custom_fields = fields.Dict(load_default=dict)


class TicketUpdateSchema(Schema):
    title = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(validate=validate.Length(min=1))
    priority = fields.String(validate=validate.OneOf(TICKET_PRIORITIES))
    category_id = fields.String(allow_none=True)
    queue_id = fields.String(allow_none=True)
    custom_fields = fields.Dict()


class TicketTransitionSchema(Schema):
    to_status = fields.String(required=True, validate=validate.OneOf(TICKET_STATUSES))
    reason = fields.String(load_default=None)


class TicketAssignSchema(Schema):
    assignee_id = fields.String(allow_none=True)


class TicketOutSchema(Schema):
    id = fields.String()
    number = fields.Integer()
    title = fields.String()
    description = fields.String()
    status = fields.String()
    priority = fields.String()
    requester_id = fields.String()
    assignee_id = fields.String(allow_none=True)
    queue_id = fields.String(allow_none=True)
    category_id = fields.String(allow_none=True)
    custom_fields = fields.Dict()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    resolved_at = fields.DateTime(allow_none=True)
    closed_at = fields.DateTime(allow_none=True)
    due_at = fields.DateTime(allow_none=True)
    sla_breach_at = fields.DateTime(allow_none=True)


class CommentCreateSchema(Schema):
    body = fields.String(required=True, validate=validate.Length(min=1))
    is_internal = fields.Boolean(load_default=False)


class CommentOutSchema(Schema):
    id = fields.String()
    ticket_id = fields.String()
    author_id = fields.String()
    body = fields.String()
    is_internal = fields.Boolean()
    created_at = fields.DateTime()
