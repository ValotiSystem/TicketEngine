"""
summary:
    Application factory. Pattern: factory + blueprints.
    No circular imports, no global state beyond Flask extensions.
"""
from __future__ import annotations

import logging
import uuid
from flask import Flask, g, request

from .config import get_config
from .extensions import db, migrate, jwt, cors, init_redis


def create_app(config_object: str | None = None) -> Flask:
    """
    summary:
        Build and configure a Flask application instance.
    args:
        config_object: optional config key ("development" or "production").
            When None, the FLASK_ENV environment variable decides.
    return:
        Configured Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_object))

    _init_extensions(app)
    _init_logging(app)
    _init_request_context(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)
    _install_observability(app)

    return app


def _init_extensions(app: Flask) -> None:
    """
    summary:
        Initialize Flask extensions, the optional Redis client and
        import all model modules so Alembic autogenerate sees them.
    args:
        app: Flask application.
    return:
        None.
    """
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )
    init_redis(app)

    from . import models  # noqa: F401


def _init_logging(app: Flask) -> None:
    """
    summary:
        Configure application logging.
    args:
        app: Flask application.
    return:
        None.
    """
    # CRITIQUE: in prod use structured logging (JSON) to stdout and let
    # an external agent collect it. Kept basic here.
    logging.basicConfig(
        level=logging.INFO if not app.debug else logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _init_request_context(app: Flask) -> None:
    """
    summary:
        Inject a request_id on every request so all logging can be
        correlated for troubleshooting.
    args:
        app: Flask application.
    return:
        None.
    """

    @app.before_request
    def _attach_request_id():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _expose_request_id(resp):
        resp.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return resp


def _register_blueprints(app: Flask) -> None:
    """
    summary:
        Register all API blueprints under their versioned prefix.
    args:
        app: Flask application.
    return:
        None.
    """
    from .auth.routes import bp as auth_bp
    from .tickets.routes import bp as tickets_bp
    from .users.routes import bp as users_bp
    from .audit.routes import bp as audit_bp
    from .admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(tickets_bp, url_prefix="/api/v1/tickets")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    app.register_blueprint(audit_bp, url_prefix="/api/v1/audit-events")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")


def _register_error_handlers(app: Flask) -> None:
    """
    summary:
        Wire up the standard error envelope handlers.
    args:
        app: Flask application.
    return:
        None.
    """
    from .common.errors import register_error_handlers
    register_error_handlers(app)


def _register_cli(app: Flask) -> None:
    """
    summary:
        Register custom Flask CLI commands (e.g. seed).
    args:
        app: Flask application.
    return:
        None.
    """
    from .cli import register_cli
    register_cli(app)


def _install_observability(app: Flask) -> None:
    """
    summary:
        Install Prometheus /metrics endpoint and per-request hooks.
    args:
        app: Flask application.
    return:
        None.
    """
    from .observability.metrics import install
    install(app)
