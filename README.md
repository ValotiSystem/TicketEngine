# TicketPortal

> Multi-tenant ticketing web application. **React + Flask + PostgreSQL + Redis + Celery.**

A scaffold built around a strict workflow state machine, tenant-aware data
access, JWT auth with refresh, immutable audit log and async notifications.
Not a finished MVP — the building blocks are in place; the surface is small
on purpose.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [API overview](#api-overview)
- [Project structure](#project-structure)
- [Workflow state machine](#workflow-state-machine)
- [Known limitations / `CRITIQUE` notes](#known-limitations--critique-notes)
- [Roadmap](#roadmap)

---

## Features

### Core ticketing
- **Multi-tenant by design** — `tenant_id` on every business row, enforced at the repository layer (no naked queries in route handlers).
- **Strict state machine** — single source of truth in `app/services/workflow.py`; status changes never bypass it.
- **RBAC + permission gate** — roles per tenant, permissions as string codes, embedded in JWT claims.
- **Per-tenant readable ticket numbers** generated through a row-locked sequencer (see `TicketNumberSequence`).
- **Public / internal comments** — visibility filtered server-side based on the requesting user's permissions.
- **Immutable audit log** — every meaningful action writes an `AuditEvent` in the same DB transaction.
- **Server-side pagination, filtering and sorting** with whitelisted sort columns.

### Auth & security
- JWT access tokens (short-lived) + refresh tokens.
- `argon2id` password hashing.
- Standardized error envelope: `{ error: { code, message, request_id } }`.
- `X-Request-ID` propagation for end-to-end tracing.
- Tenant context required in every authenticated request (no "global" tokens).

### Async / scalability
- Celery + Redis for notifications, SLA scanning, indexing.
- Notifications enqueued **after** DB commit (with documented outbox-pattern caveat).
- Indices on every common ticket filter combination.

### Frontend
- Vite + TypeScript + React 18.
- Centralized API client with automatic token refresh on 401.
- Zustand store (persisted) for session state.
- React Query for server state caching with sane defaults.
- Permission-aware UI: actions conditionally rendered based on JWT claims.

---

## Tech stack

| Layer | Tech |
|------|------|
| Frontend | React 18, TypeScript, Vite, React Router, React Query, Zustand |
| Backend | Flask 3, SQLAlchemy 2, Flask-Migrate (Alembic), Flask-JWT-Extended, Marshmallow |
| Database | PostgreSQL 16 (SQLite for the lightest dev workflow) |
| Cache / broker | Redis 7 |
| Async | Celery 5 |
| Auth | JWT (access + refresh), Argon2 password hashing |
| Container | Docker / docker-compose for local dev |

---

## Architecture

High-level component view:

![Architecture](docs/screenshots/architecture.png)

> Source: [`docs/architecture.puml`](docs/architecture.puml). Render with any PlantUML viewer.

Data model:

![Data model](docs/screenshots/data-model.png)

> Source: [`docs/data-model.puml`](docs/data-model.puml).

Ticket lifecycle:

![State machine](docs/screenshots/state-machine.png)

> Source: [`docs/state-machine.puml`](docs/state-machine.puml).

---

## Screenshots

> Drop PNGs into `docs/screenshots/` to make these render on GitHub.

### Login
![Login](docs/screenshots/login.png)

### Ticket list
![Ticket list](docs/screenshots/tickets.png)

### Ticket detail with state transitions and comments
![Ticket detail](docs/screenshots/ticket-detail.png)

### New ticket form
![New ticket](docs/screenshots/new-ticket.png)

---

## Quick start

### Option A — Docker (recommended)

```bash
docker compose up -d postgres redis
docker compose up backend frontend
```

The frontend is served on `http://localhost:5173`, the backend API on `http://localhost:5000`.

### Option B — Local

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

flask --app wsgi db init            # first time only
flask --app wsgi db migrate -m "init"
flask --app wsgi db upgrade
flask --app wsgi seed               # creates demo tenant + admin user
flask --app wsgi run --debug
```

```bash
# Frontend (in a second terminal)
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Demo credentials (seed only — change before going live)

| Field   | Value             |
|---------|-------------------|
| Tenant  | `acme`            |
| Email   | `admin@acme.test` |
| Password| `admin123`        |

---

## API overview

All endpoints are versioned under `/api/v1/`.

### Auth
| Method | Path                  | Description |
|--------|-----------------------|-------------|
| POST   | `/auth/login`         | Exchange credentials for token pair |
| POST   | `/auth/refresh`       | Issue a new access token |
| GET    | `/auth/me`            | Current user + permissions |
| POST   | `/auth/logout`        | Audit-only logout (see notes) |

### Tickets
| Method | Path                              | Description |
|--------|-----------------------------------|-------------|
| GET    | `/tickets`                        | List with filters / pagination |
| POST   | `/tickets`                        | Create |
| GET    | `/tickets/{id}`                   | Detail |
| PATCH  | `/tickets/{id}`                   | Partial update |
| GET    | `/tickets/{id}/comments`          | List comments (internal filtered) |
| POST   | `/tickets/{id}/comments`         | Add comment |
| POST   | `/tickets/{id}/assign`           | Change assignee |
| POST   | `/tickets/{id}/transition`       | Move to a new status |

### Audit
| Method | Path             | Description |
|--------|------------------|-------------|
| GET    | `/audit-events`  | Tenant-scoped audit log with filters |

### Standard error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Title is required",
    "field": "title",
    "request_id": "9f2b…"
  }
}
```

---

## Project structure

```
TicketPortal/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Application factory
│   │   ├── config.py            # Environment config classes
│   │   ├── extensions.py        # SQLAlchemy, JWT, CORS, Migrate
│   │   ├── cli.py               # Flask CLI commands (seed)
│   │   ├── common/              # Errors, responses, decorators
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Marshmallow schemas
│   │   ├── repositories/        # Tenant-aware data access
│   │   ├── services/            # Domain logic + workflow state machine
│   │   ├── auth/                # Auth blueprint
│   │   ├── tickets/             # Tickets blueprint
│   │   ├── users/               # Users blueprint
│   │   ├── audit/               # Audit blueprint
│   │   └── tasks/               # Celery tasks (notifications, SLA)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── wsgi.py
├── frontend/
│   ├── src/
│   │   ├── api/                 # HTTP client + per-resource modules
│   │   ├── components/          # Shared UI
│   │   ├── features/tickets/    # Ticket-specific UI + workflow mirror
│   │   ├── pages/               # Route pages
│   │   ├── routes/              # Routing + auth guard
│   │   ├── store/               # Zustand stores
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── architecture.puml
│   ├── data-model.puml
│   └── state-machine.puml
├── docker-compose.yml
└── README.md
```

---

## Workflow state machine

```
draft → open → triage → in_progress → resolved → closed
                  ↓          ↘             ↓
            waiting_on_*  waiting_on_*  reopened
                  ↓
              cancelled (terminal)
```

Full transition map and reasoning live in
[`backend/app/services/workflow.py`](backend/app/services/workflow.py).
The frontend mirrors the rules in
[`frontend/src/features/tickets/workflow.ts`](frontend/src/features/tickets/workflow.ts) —
the backend remains the source of truth.

Two transitions require a mandatory reason:
- `* → resolved` (resolution reason)
- `* → cancelled` (cancellation reason)

---

## Known limitations / `CRITIQUE` notes

This scaffold is honest about what it isn't. Search the codebase for
`CRITIQUE:` to find every flagged trade-off. The headline ones:

| File | Issue |
|------|-------|
| `services/ticket_service.py` | Notifications use direct `delay()` enqueue. Outbox pattern recommended for crash safety. |
| `repositories/ticket_repository.py` | Per-tenant ticket number sequencer relies on `SELECT ... FOR UPDATE`; SQLite degrades silently. |
| `models/ticket.py` | `custom_fields` stored as JSON. For complex search, switch to EAV or add a Postgres GIN index. |
| `models/audit.py` | DB-level immutability (trigger BEFORE UPDATE) not enforced; relies on convention. |
| `repositories/ticket_repository.py` | Search uses `ILIKE`; switch to Postgres FTS or external engine past ~100k tickets. |
| `auth/routes.py` | Logout has no JWT blocklist — token remains valid until expiry. |
| `store/auth.ts` | Tokens stored in `localStorage` — XSS-sensitive. Consider httpOnly cookies for high-trust scenarios. |
| `tasks/notifications.py` | Stub only. Real notifications need templates, multi-channel routing, dedup keys, dead-letter queue. |

---

## Roadmap

**Phase 1 (current scaffold)** — login, ticket CRUD, comments, transitions, assignments, basic audit.

**Phase 2** — full RBAC seeding, SLA engine, queues UI, email notifications, custom fields UI, advanced search.

**Phase 3** — webhooks, dashboard metrics, SSO/SAML, full-text search engine, attachment AV scanning, ticket import.

---

## License

MIT. See [LICENSE](LICENSE) (add one before publishing).
