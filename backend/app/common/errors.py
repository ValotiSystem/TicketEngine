"""
summary:
    Application errors and the standard response envelope.

    The error envelope is a stable contract with the frontend:
    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "human readable",
        "field": "title",            # optional
        "request_id": "uuid"
      }
    }
"""
from __future__ import annotations

from flask import g, jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None, *, field: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.field = field


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 400


class AuthRequired(AppError):
    code = "AUTH_REQUIRED"
    http_status = 401
    message = "Authentication required"


class Forbidden(AppError):
    code = "FORBIDDEN"
    http_status = 403
    message = "Operation not allowed"


class NotFound(AppError):
    code = "NOT_FOUND"
    http_status = 404
    message = "Resource not found"


class Conflict(AppError):
    code = "CONFLICT"
    http_status = 409


class RateLimited(AppError):
    code = "RATE_LIMITED"
    http_status = 429
    message = "Too many requests"


class InvalidTransition(AppError):
    code = "INVALID_TRANSITION"
    http_status = 409


def _build(code: str, message: str, status: int, field: str | None = None):
    """
    summary:
        Produce the standard error response payload.
    args:
        code: machine-readable error code.
        message: human-readable error message.
        status: HTTP status code.
        field: optional field name responsible for the error.
    return:
        Tuple (Flask Response, status code).
    """
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(g, "request_id", None),
        }
    }
    if field:
        payload["error"]["field"] = field
    return jsonify(payload), status


def register_error_handlers(app):
    """
    summary:
        Wire AppError, HTTPException and uncaught exceptions to the
        standard response envelope.
    args:
        app: Flask application.
    return:
        None.
    """
    @app.errorhandler(AppError)
    def _app_error(err: AppError):
        return _build(err.code, err.message, err.http_status, err.field)

    @app.errorhandler(HTTPException)
    def _http_error(err: HTTPException):
        # CRITIQUE: do NOT propagate werkzeug descriptions if they may contain
        # internal paths. We use the status name only; customise where needed.
        return _build(err.name.upper().replace(" ", "_"), err.description or err.name, err.code or 500)

    @app.errorhandler(Exception)
    def _unhandled(err: Exception):
        # Never leak stack traces to the client. Log on the server side.
        app.logger.exception("Unhandled exception", exc_info=err)
        return _build("INTERNAL_ERROR", "Internal error", 500)
