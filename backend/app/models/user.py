"""
summary:
    User model with argon2 password hashing.
"""
from sqlalchemy import Column, String, Boolean, UniqueConstraint
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..extensions import db
from .base import UUIDPk, Timestamps, tenant_id_column

_hasher = PasswordHasher()


class User(UUIDPk, Timestamps, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        # email unique per tenant: the same address can exist on different tenants
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )

    tenant_id = tenant_id_column()
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # CRITIQUE: a cross-tenant "platform admin" exists but must always
    # operate with a selected tenant. It does not bypass tenant_id filters.
    is_platform_admin = Column(Boolean, default=False, nullable=False)

    def set_password(self, raw: str) -> None:
        """
        summary:
            Hash and store the given plaintext password.
        args:
            raw: plaintext password.
        return:
            None.
        """
        self.password_hash = _hasher.hash(raw)

    def check_password(self, raw: str) -> bool:
        """
        summary:
            Verify a plaintext password against the stored hash.
        args:
            raw: plaintext password candidate.
        return:
            True when the password matches, False otherwise.
        """
        try:
            return _hasher.verify(self.password_hash, raw)
        except VerifyMismatchError:
            return False
