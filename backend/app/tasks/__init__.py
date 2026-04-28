"""
summary:
    Celery application + task auto-discovery.
"""
from __future__ import annotations

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ticketportal",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.notifications", "app.tasks.sla"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
