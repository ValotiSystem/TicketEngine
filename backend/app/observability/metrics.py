"""
summary:
    Prometheus metrics exposition.

    The /metrics endpoint is unauthenticated by design: scrape it from
    the cluster network, never expose it publicly. Add a network ACL
    or, in Kubernetes, a NetworkPolicy. The metrics are best consumed
    by a `prometheus-operator` ServiceMonitor pointed at the backend
    service.
"""
from __future__ import annotations

import time

from flask import Blueprint, Response, request, g
from prometheus_client import (
    CollectorRegistry, Counter, Histogram, generate_latest,
    CONTENT_TYPE_LATEST,
)

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests by method, path template and status code.",
    ["method", "path", "status"],
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, bucketed for SLO tracking.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)

bp = Blueprint("metrics", __name__)


@bp.get("")
def metrics():
    """
    summary:
        Expose Prometheus metrics in the text exposition format.
    args:
        none.
    return:
        Flask Response with Content-Type expected by Prometheus.
    """
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


def install(app):
    """
    summary:
        Register the /metrics blueprint and the per-request hooks that
        feed REQUEST_COUNT and REQUEST_LATENCY.
    args:
        app: Flask application.
    return:
        None.
    """
    app.register_blueprint(bp, url_prefix="/metrics")

    @app.before_request
    def _start_timer():
        g._metric_t0 = time.perf_counter()

    @app.after_request
    def _record(resp):
        # Use the matched URL rule pattern (e.g. "/api/v1/tickets/<id>")
        # so cardinality stays bounded. Falling back to "unknown"
        # prevents an explosion when a 404 has no rule.
        rule = request.url_rule.rule if request.url_rule else "unknown"
        elapsed = time.perf_counter() - g.pop("_metric_t0", time.perf_counter())
        REQUEST_LATENCY.labels(request.method, rule).observe(elapsed)
        REQUEST_COUNT.labels(request.method, rule, str(resp.status_code)).inc()
        return resp
