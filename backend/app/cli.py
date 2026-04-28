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


@click.command("seed")
@with_appcontext
def seed_command():
    """
    summary:
        Minimal seed: 1 tenant, 1 admin, an Agent role with all base
        permissions.
    args:
        none.
    return:
        None.
    """
    if db.session.query(Tenant).first():
        click.echo("Already seeded. Skipping.")
        return

    # Permissions
    perms_by_code = {}
    for code, desc in STANDARD_PERMISSIONS:
        p = Permission(code=code, description=desc)
        db.session.add(p)
        perms_by_code[code] = p
    db.session.flush()

    # Tenant
    tenant = Tenant(name="Acme", slug="acme")
    db.session.add(tenant)
    db.session.flush()

    # Agent role with every permission
    role = Role(tenant_id=tenant.id, name="Agent")
    db.session.add(role)
    db.session.flush()
    for code, p in perms_by_code.items():
        db.session.add(RolePermission(role_id=role.id, permission_id=p.id))

    # Admin user
    admin = User(
        tenant_id=tenant.id,
        email="admin@acme.test",
        full_name="Acme Admin",
        is_active=True,
        is_platform_admin=True,
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.flush()
    db.session.add(UserRole(user_id=admin.id, role_id=role.id))

    db.session.commit()
    click.echo("Seed completed. Login: tenant=acme email=admin@acme.test password=admin123")


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
