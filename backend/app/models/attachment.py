"""
summary:
    Attachment metadata. Real bytes live in object storage.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Index

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column


class Attachment(UUIDPk, Timestamps, db.Model):
    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachment_ticket", "ticket_id"),
    )

    tenant_id = tenant_id_column()
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    uploader_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    filename = Column(String(255), nullable=False)

    # CRITIQUE: MIME must be verified server-side (magic bytes), NOT just
    # accepted from the client. See services/attachment_service (future).
    mime = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)

    # Bucket key. Never expose directly: download via signed URL.
    storage_key = Column(String(500), nullable=False, unique=True)

    # pending | clean | infected | error
    scan_status = Column(String(20), nullable=False, default="pending")
