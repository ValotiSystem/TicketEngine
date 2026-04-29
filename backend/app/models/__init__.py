"""
summary:
    Model aggregator. Import every new model here so Alembic
    autogenerate can detect it.
"""
from .tenant import Tenant  # noqa: F401
from .user import User  # noqa: F401
from .role import Role, UserRole  # noqa: F401
from .permission import Permission, RolePermission  # noqa: F401
from .queue import Queue  # noqa: F401
from .category import TicketCategory  # noqa: F401
from .sla import SLAPolicy  # noqa: F401
from .ticket import Ticket, TicketNumberSequence  # noqa: F401
from .comment import Comment  # noqa: F401
from .attachment import Attachment  # noqa: F401
from .audit import AuditEvent  # noqa: F401
from .tag import Tag, TicketTag  # noqa: F401
from .custom_field import CustomFieldDefinition  # noqa: F401
from .outbox import OutboxEvent  # noqa: F401
