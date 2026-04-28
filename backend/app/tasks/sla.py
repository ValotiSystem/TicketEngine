"""
summary:
    SLA scheduler (stub).

    CRITIQUE: in production this task runs via celery beat every N
    minutes, and for every open ticket:
    - computes due_at and sla_breach_at if not already set
    - if X minutes from breach: emits a warning event
    - if breached: escalation + reassignment per policy
"""
from __future__ import annotations

import logging

from . import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="sla.scan_breaches")
def scan_breaches():
    """
    summary:
        Scan tickets for SLA breaches. Currently a stub.
    args:
        none.
    return:
        Dict with counters of checked / breached tickets.
    """
    log.info("SLA scan (stub)")
    return {"checked": 0, "breached": 0}
