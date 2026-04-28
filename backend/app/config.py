"""
summary:
    Per-environment configuration. No hard-coded constants in
    application code.
"""
from __future__ import annotations

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-not-for-prod")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///./instance/ticketportal.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-not-for-prod")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MIN", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    STORAGE_LOCAL_PATH = os.getenv("STORAGE_LOCAL_PATH", "./storage")

    # CRITIQUE: these limits should also be enforced at the nginx/gateway
    # level, not only in Flask. This is just the application-level defence.
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB upload
    ATTACHMENT_MIME_WHITELIST = {
        "image/png", "image/jpeg", "image/gif", "image/webp",
        "application/pdf",
        "text/plain", "text/csv",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False


def get_config(name: str | None = None):
    """
    summary:
        Resolve the config class for the requested environment.
    args:
        name: optional environment name ("development" or "production").
            When None, FLASK_ENV is used; falls back to development.
    return:
        Config class to be passed to Flask.config.from_object.
    """
    env = (name or os.getenv("FLASK_ENV", "development")).lower()
    return {"production": ProdConfig, "development": DevConfig}.get(env, DevConfig)
