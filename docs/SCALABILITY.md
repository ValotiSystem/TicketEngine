# Scalability playbook

This document is the honest map between **what is implemented in the
scaffold** and **what would still need to be built or tuned** to push
the system into the multi-region, hundreds-of-millions-of-tickets
territory.

The goal is not "buzzword bingo". Each pattern listed below either
solves a specific bottleneck observed in real ticketing platforms (Zendesk,
ServiceNow, Jira Service Management) or hardens a known failure mode.

---

## Implemented in the scaffold

### 1. Transactional outbox

Code: [`app/services/outbox.py`](../backend/app/services/outbox.py),
[`app/tasks/outbox_drain.py`](../backend/app/tasks/outbox_drain.py).

Events are written to `outbox_events` in the **same transaction** as
the business state change. A celery beat task drains the table every
two seconds using `SELECT … FOR UPDATE SKIP LOCKED`, so multiple
workers can pull the queue in parallel without contention. This
eliminates the "DB committed but broker enqueue lost" failure mode.

A partial index `WHERE dispatched_at IS NULL` keeps the drain query
sub-millisecond even when the table grows to billions of rows.

### 2. Per-tenant tenant-aware repositories

Every repository function takes `tenant_id` as the first argument and
filters every query. There is **no path** in the codebase that returns
a row without the tenant filter. This is the foundation for both
correctness (data isolation) and shardability (the partitioning key is
already on every query).

### 3. Keyset (cursor) pagination

Code: [`app/repositories/cursor.py`](../backend/app/repositories/cursor.py).

The list endpoint supports both offset and cursor pagination. Cursor
mode uses a strict `(created_at, id) < (last_created_at, last_id)`
clause served by the compound index `(tenant_id, created_at, id)`.
Cost per page is **O(log N + page_size)** regardless of how deep the
client scrolls.

### 4. Postgres full-text search with GIN index

Code: [`app/models/ticket.py`](../backend/app/models/ticket.py)
(`search_vector` column),
[`app/repositories/ticket_repository.py`](../backend/app/repositories/ticket_repository.py)
(`update_search_vector`, FTS-vs-ILIKE switch).

Tickets carry a `tsvector` column populated on title/description
changes, with weights `A` (title) and `B` (description). A GIN index
serves `plainto_tsquery` matches. SQLite dev falls back to ILIKE.

### 5. Redis-backed primitives (fail-open)

| Primitive | File | Purpose |
|-----------|------|---------|
| Cache | [`app/common/cache.py`](../backend/app/common/cache.py) | Permission set caching (60s TTL) and generic key-value cache |
| Rate limit | [`app/common/rate_limit.py`](../backend/app/common/rate_limit.py) | Token-bucket per (scope, user/ip) |
| Idempotency-Key | [`app/common/idempotency.py`](../backend/app/common/idempotency.py) | Replays cached responses for retries on the same key |

Every primitive is **fail-open**: if Redis is unreachable the request
still flows through. A degraded cache must never become a degraded
service.

### 6. Read replica routing scaffold

Code: [`app/db/routing.py`](../backend/app/db/routing.py).

Two engines (writer + reader) wired by env var
`DATABASE_URL_REPLICA`. When unset the reader silently falls back to
the writer so single-instance deployments keep working without
configuration changes.

Replica-lag pitfall ("read your own writes") is documented inline:
pin reads to primary for the lifetime of any request that performed a
write, or use sticky-session-on-tenant for a few hundred ms after a
write.

### 7. Per-tenant compound indexes

The `tickets` table is indexed on every common query shape:

```
(tenant_id, status)          – queue / inbox views
(tenant_id, assignee_id)     – "my tickets"
(tenant_id, queue_id)        – queue boards
(tenant_id, requester_id)    – requester portal
(tenant_id, due_at)          – SLA scanner
(tenant_id, created_at, id)  – keyset pagination
GIN(search_vector)           – FTS
unique(tenant_id, number)    – sequencer
```

### 8. Prometheus metrics

Code: [`app/observability/metrics.py`](../backend/app/observability/metrics.py).

`http_requests_total{method,path,status}` and
`http_request_duration_seconds{method,path}` exposed at `/metrics`,
labels keyed on the **URL rule pattern** so cardinality stays bounded
even under high traffic.

### 9. Standardized error envelope and request_id correlation

Every response carries `X-Request-ID` (echoed when supplied or
generated server-side); every error response embeds it in the body.
Logs are correlated by request id end to end.

### 10. JWT with refresh + permission claims

Permissions are baked into the access token at login, so the request
path skips the role-permission join entirely. Cache invalidation on
role change is supported but not yet wired.

---

## Documented but not implemented (clear next steps)

These are intentionally outside the scaffold to keep it readable. Each
has a one-line implementation sketch.

| Pattern | Sketch |
|--------|--------|
| **Sharding by tenant_id** | Wrap the writer/reader engines with a routing layer that consistent-hashes `tenant_id` to one of N physical shards. Citus does this transparently for Postgres. |
| **Search engine** | Replace the Postgres FTS path with Meilisearch or OpenSearch when ticket count crosses ~50M. The repository abstraction means only `_base_filtered` changes. |
| **Materialized counters** | Dashboards (open / closed / SLA-breached per queue) should not run `COUNT(*)` on the live table. Maintain incremental counters in a small `tenant_counters` table updated by audit triggers, refresh on a 30s loop. |
| **Audit partitioning** | `audit_events` grows monotonically; partition by `(tenant_id, month)` and detach old partitions to cold storage. |
| **Object storage signed URLs** | Attachments already point at object storage; generate per-request signed URLs with a 5-minute TTL so the API never proxies bytes. |
| **CDN for the SPA** | The Vite build is fully static; ship via a CDN (Cloudflare/Fastly) so latency is local for every region. |
| **Multi-region writes** | If you need <50ms write latency globally, shard by tenant home-region and replicate cross-region with logical replication. Cross-tenant queries become impossible — accept the trade. |
| **Service worker for read views** | Cache GETs of tickets and comments client-side so an offline agent can keep reading. Writes still require connectivity. |
| **OpenTelemetry tracing** | Add `opentelemetry-instrumentation-flask` + an OTLP exporter to a backend like Tempo/Jaeger. Every Flask request becomes a span; SQLAlchemy queries get child spans automatically. |

---

## Operational guardrails that matter more than any code

- **Statement timeout**: set `statement_timeout = 5s` on the Postgres
  user used by the API. A runaway SELECT must not block other tenants.
- **Connection pool ceilings**: gunicorn workers × pool_size must stay
  well under Postgres `max_connections`. Use PgBouncer in transaction
  pooling mode in front.
- **Backpressure on Celery**: cap `worker_prefetch_multiplier=1` on
  the outbox drain so a single slow event does not starve siblings.
- **Backups**: physical backups (pg_basebackup + WAL archive) every
  24h, point-in-time-recovery window of at least 7 days, restore
  drill quarterly. Untested backups are myths.
- **Capacity planning rule of thumb**: 1 vCPU and 4GB of RAM per ~500
  RPS of cached-permission read traffic on the API; 1 vCPU per 50
  writes/s sustained on Postgres if you keep the indexes above.
