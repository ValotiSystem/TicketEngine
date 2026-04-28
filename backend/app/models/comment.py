"""
summary:
    Comment model. Supports public and internal visibility.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean, Index

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class Comment(UUIDPk, Timestamps, db.Model):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comment_ticket_created", "ticket_id", "created_at"),
    )

    tenant_id = tenant_id_column()
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    body = Column(Text, nullable=False)

    # CRITIQUE: distinguishing internal vs public is essential. Visibility is
    # filtered server-side: the frontend must never receive internal comments
    # if the user lacks the ticket.comment_internal permission.
    is_internal = Column(Boolean, nullable=False, default=False)
