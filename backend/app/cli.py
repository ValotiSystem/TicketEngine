"""
summary:
    Flask CLI commands for development data seeding.

    Usage:
      flask --app wsgi seed
"""
from __future__ import annotations

import click
from flask.cli import with_appcontext

from .extensions import db
from .models.tenant import Tenant
from .models.user import User
from .models.role import Role, UserRole
from .models.permission import Permission, RolePermission, STANDARD_PERMISSIONS
from .models.queue import Queue
from .models.category import TicketCategory


# Role -> permission code matrix used by the seed.
# Keep this matrix small and readable: a real installation builds the
# matrix from the admin UI. The shape is intentionally explicit so
# new contributors can reason about permission boundaries at a glance.
ROLE_MATRIX: dict[str, list[str]] = {
    "Requester": [
        "ticket.create",
        "ticket.read",
    ],
    "Agent": [
        "ticket.create",
        "ticket.read",
        "ticket.read_all",
        "ticket.update",
        "ticket.assign",
        "ticket.transition",
        "ticket.comment_internal",
        "ticket.close",
        "ticket.reopen",
    ],
    "Supervisor": [
        "ticket.create",
        "ticket.read",
        "ticket.read_all",
        "ticket.update",
        "ticket.assign",
        "ticket.transition",
        "ticket.comment_internal",
        "ticket.close",
        "ticket.reopen",
        "ticket.reopen_closed",
        "audit.read",
    ],
    "Admin": [code for code, _ in STANDARD_PERMISSIONS],
}


@click.command("seed")
@with_appcontext
def seed_command():
    """
    summary:
        Seed two demo tenants (acme, globex) with all four standard roles
        and a demo user per role on each tenant. Includes a default queue
        and a small category tree per tenant.
    args:
        none.
    return:
        None.
    """
    if db.session.query(Tenant).first():
        click.echo("Already seeded. Skipping.")
        return

    # 1. Permissions catalogue (global)
    perms = {}
    for code, desc in STANDARD_PERMISSIONS:
        p = Permission(code=code, description=desc)
        db.session.add(p)
        perms[code] = p
    db.session.flush()

    for slug, name in [("acme", "Acme Inc."), ("globex", "Globex Corp.")]:
        _seed_tenant(slug=slug, name=name, perms=perms)

    db.session.commit()

    click.echo("")
    click.echo("Seed completed. Demo accounts (password: 'password' for all):")
    click.echo("  Tenant 'acme'   - admin@acme.test, supervisor@acme.test, agent@acme.test, requester@acme.test")
    click.echo("  Tenant 'globex' - admin@globex.test, supervisor@globex.test, agent@globex.test, requester@globex.test")


def _seed_tenant(*, slug: str, name: str, perms: dict[str, Permission]) -> None:
    """
    summary:
        Seed a single tenant with all standard roles, a demo user per
        role, a default queue and a small category tree.
    args:
        slug: tenant slug (URL-safe identifier).
        name: human-readable tenant name.
        perms: mapping permission_code -> Permission instance.
    return:
        None.
    """
    tenant = Tenant(slug=slug, name=name)
    db.session.add(tenant)
    db.session.flush()

    # Roles + role->permission mappings
    role_objs: dict[str, Role] = {}
    for role_name, codes in ROLE_MATRIX.items():
        role = Role(tenant_id=tenant.id, name=role_name)
        db.session.add(role)
        db.session.flush()
        for code in codes:
            db.session.add(RolePermission(role_id=role.id, permission_id=perms[code].id))
        role_objs[role_name] = role

    # Default queue
    queue = Queue(tenant_id=tenant.id, name="General", description="Default catch-all queue")
    db.session.add(queue)

    # Small category tree
    root = TicketCategory(tenant_id=tenant.id, name="IT")
    db.session.add(root)
    db.session.flush()
    for child in ("Hardware", "Software", "Access"):
        db.session.add(TicketCategory(tenant_id=tenant.id, name=child, parent_id=root.id))

    # One demo user per role
    for role_name in ROLE_MATRIX:
        local = role_name.lower()
        user = User(
            tenant_id=tenant.id,
            email=f"{local}@{slug}.test",
            full_name=f"{slug.capitalize()} {role_name}",
            is_active=True,
            is_platform_admin=(role_name == "Admin"),
        )
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_id=role_objs[role_name].id))


def register_cli(app):
    """
    summary:
        Register CLI commands on the Flask application.
    args:
        app: Flask application.
    return:
        None.
    """
    app.cli.add_command(seed_command)
