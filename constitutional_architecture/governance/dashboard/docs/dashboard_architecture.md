# Governance Dashboard — Architecture

Phase 28 · Milestone 5A · `governance/dashboard/`

## 1. Position in the platform

```
Evolution Engine / PEP  ──▶  Governance Kernel  ◀──  Dashboard BFF  ◀──  Browser
      (policy enforcer)      (single system of record)   (this module)
```

The dashboard is a **thin backend-for-frontend (BFF)**: it renders HTML,
handles sessions and CSRF, and proxies to the kernel. It holds **no
governance state** of its own. If the dashboard disappears, governance is
unaffected; if the kernel is unavailable, the dashboard fails closed.

## 2. Module map

| Module | Responsibility |
|--------|----------------|
| `app.py` | FastAPI application factory `create_app(client, config, metrics)`; routes; exception handlers; `/health/*`; `/metrics`; `demo_app()` wiring |
| `client.py` | `GovernanceDashboardClient` — the only way the UI talks to governance; fail-closed `_guard`; view-model mapping; redaction |
| `service.py` | `DashboardService` — kernel-facing read models and mutations (prior milestone layer) |
| `auth.py` | `SessionManager`, `Authenticator`, session/CSRF token helpers |
| `config.py` | `DashboardConfig` — roles, permissions, users, redaction keys, session TTL |
| `errors.py` | `DashboardError` hierarchy (401/403/404/422/503) |
| `view_models.py` | Presentation dataclasses + `redact()` |
| `templates/` | Jinja2 server-rendered pages (24 templates) |
| `static/` | `styles.css`, `app.js` (CSRF injection for forms) |
| `tests/` | Web BFF tests (79 tests: auth, views, approvals, exceptions, audit integrity, lineage) |
| `docs/` | This architecture note, operator guide, security model |
| `render_console.py` / `console.html` | Prior milestone: static self-contained console artifact |

## 3. Request lifecycle

```
Browser ──GET /approvals──▶ app.py route
   │
   ├─ session_token_from_request(request) ──▶ Authenticator.require_user ──▶ 401 page?
   ├─ client.list_approvals()                (read path; no CSRF needed)
   │     └─ DashboardService.approvals ──▶ GovernanceKernel (in-process)
   └─ render() ──▶ Jinja2Templates(base.html + approvals/queue.html)
```

```
Browser ──POST /approvals/{id}/approve (form: comment, csrf_token)──▶ route
   │
   ├─ require(user, "approve")                     ──▶ 403 page?
   ├─ require_csrf(session, token)                 ──▶ 403 page?
   ├─ user.to_actor(config)                        (HUMAN actor, kernel roles)
   ├─ client.submit_approval_decision(id, actor, "APPROVED", comment)
   │     └─ DashboardService.approve ──▶ kernel.submit_approval(..., actor)
   │             └─ audit.record APPROVAL_DECIDED (hash-chained)
   └─ 303 → /approvals/{id}
```

## 4. Design rules

1. **The kernel is the only backend.** `DashboardService` reads kernel state;
   mutations call kernel APIs. The dashboard never writes its own store.
2. **Thin presentation.** All data crosses the boundary as view models
   (`view_models.py`); templates only format.
3. **Fail closed.** Any kernel error is surfaced as 503 with an explicit
   "unavailable" page; errors are typed (401/403/404/422/503) so operators
   can distinguish misuse from outage.
4. **Authorization is checked twice.** The dashboard enforces its role
   matrix; the kernel re-checks the constructed actor. Kernel denials are
   displayed, not hidden.
5. **One redaction point.** `redact()` runs in `client.py` for every payload
   so no template can leak a sensitive key.
6. **Deterministic, no hidden state.** Decision IDs are content-addressed;
   the same request always yields the same decision, so reconstruction is
   exact.

## 5. Observability

- `/health/live` — process liveness (no auth, for load balancers).
- `/health/ready` — kernel, auth, templates, static (dependency probe).
- `/metrics` — counters per spec §12: page views, API errors, kernel request
  duration, approval actions, exception revocations, audit verifications.

## 6. Test strategy

`tests/` drives the BFF with FastAPI's `TestClient` against a demo kernel:

- `test_dashboard_auth.py` — sessions, CSRF, role matrix, kernel denials,
  fail-closed;
- `test_dashboard_views.py` — every section renders with kernel-derived
  values, redaction, readiness;
- `test_dashboard_approvals.py` — approve/reject through the BFF, audit
  visibility, double-decision rejection;
- `test_dashboard_exceptions.py` — listing, revocation, audit visibility,
  permissions;
- `test_dashboard_audit_integrity.py` — VALID chain, tamper detection,
  first-broken-event reporting, fail-closed;
- `test_dashboard_lineage.py` — explorer, backward/forward traces.

Run with:

```powershell
python -m pytest constitutional_architecture/governance/dashboard/tests -q
```
