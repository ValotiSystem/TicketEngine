"""
summary:
    Celery application + task auto-discovery + beat schedule.
"""
from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ticketportal",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.notifications",
        "app.tasks.sla",
        "app.tasks.outbox_drain",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Beat schedule. Granularity is intentionally low (a few seconds)
    # so latency between business commit and notification stays small.
    beat_schedule={
        "outbox-drain-every-2s": {
            "task": "outbox.drain",
            "schedule": 2.0,
        },
        "sla-scan-every-minute": {
            "task": "sla.scan_breaches",
            "schedule": crontab(minute="*"),
        },
    },
)
