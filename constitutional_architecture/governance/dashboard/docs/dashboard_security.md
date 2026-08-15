# Governance Dashboard — Security Model

Phase 28 · Milestone 5A · `governance/dashboard/`

Security posture, per the Milestone 5A specification:

> Every protected route requires an authenticated session; every
> state-changing POST requires a CSRF token; kernel failures fail closed;
> the kernel's authorization is authoritative.

## 1. Threat model

| Threat | Mitigation |
|--------|------------|
| Anonymous access to governance state | Session authentication on every protected route (401). |
| Cross-site request forgery on mutations | Per-session CSRF token required on every POST (403 otherwise). |
| Privilege escalation (viewer approves, approver revokes) | Role → permission matrix; kernel role mapping checked at the kernel layer. |
| Kernel failure silently "allowing" | Fail-closed 503: no page renders and no mutation proceeds without the kernel. |
| Sensitive context values leaking into pages | Redaction of secret-like keys before rendering. |
| Session hijacking via cookie | HttpOnly + SameSite=Lax session cookie. |
| Tampered audit history going unnoticed | Hash-chain verification with first-broken-event reporting. |

## 2. Authentication & sessions

- `POST /login` validates credentials against `config.users` and issues a
  session token stored in the `gov_session` cookie
  (`HttpOnly`, `SameSite=Lax`).
- Sessions live in `SessionManager` (in-memory, `session_ttl_seconds`,
  default 1 hour) and are destroyed by `POST /logout`.
- Every protected route calls `require_user(session_token)`; failures render
  `errors/unauthorized.html` (401).
- The session carries the user's **roles only** — no kernel secrets.

## 3. Authorization

Two layers, both enforced:

1. **Dashboard layer** — role → permission matrix (`config.py`):

   | Role | Permissions |
   |------|-------------|
   | `governance_viewer` | read |
   | `governance_auditor` | read, verify_integrity |
   | `governance_approver` | read, approve, reject |
   | `governance_operator` | read, approve, reject, revoke_exception, verify_integrity |
   | `governance_admin` | read, approve, reject, revoke_exception, verify_integrity |

2. **Kernel layer** — the dashboard constructs a `HUMAN` actor whose roles
   come from `kernel_role_map`; the kernel-side service authorization
   (`DashboardService._authorize`) re-checks the actor. A kernel denial is
   surfaced as **403 "Kernel denied: ..."** — the dashboard never overrides
   the kernel.

## 4. CSRF

- Each session gets a random CSRF token (`secrets.token_urlsafe(24)`).
- Every mutation handler (`approve`, `reject`, `revoke`, `verify`) requires
  the token: read from the `csrf_token` form field (rendered as a hidden
  input in every mutation form) or the `X-CSRF-Token` header.
- Comparison uses `secrets.compare_digest`.
- The token is exposed to the page via a `<meta name="csrf-token">` tag for
  scripts; forms embed it as a hidden field.

## 5. Redaction

Context payloads are scrubbed before rendering: any key whose name contains
`secret`, `token`, `password`, `passwd`, `credential`, `api_key`, or
`private_key` is replaced with `[REDACTED]` (`view_models.redact`).
Redaction happens once, in the presentation layer, for every view.

## 6. Fail-closed behaviour

`GovernanceDashboardClient._guard` wraps every kernel interaction:

- kernel failures → `KernelUnavailableError` → **503** page ("the dashboard
  fails closed — nothing proceeds while governance is unavailable");
- unknown decisions/approvals/exceptions → 404;
- invalid input (e.g., deciding an already-decided approval) → 422;
- kernel-side authorization denials → 403, never swallowed.

## 7. Observable security events

`/metrics` exposes, among others:

- `dashboard_api_errors_total` — handled client/5xx errors;
- `dashboard_approval_actions_total`,
  `dashboard_exception_revocations_total`,
  `dashboard_audit_verification_total` — human decision workload.

Authorization failures are logged with route and error type. All approved
decisions, exception revocations, and integrity verifications also appear in
the kernel audit log itself (single system of record).

## 8. Production hardening notes

- Replace in-memory sessions with server-side sessions in a store (e.g.,
  Redis) or stateless signed sessions; keep `compare_digest` CSRF checks.
- Replace demo users with OIDC; map identity claims to the five roles.
- Terminate TLS at the proxy; the session cookie must stay `Secure`.
- Put `/metrics` and `/health/*` behind monitoring authentication or a
  network-level allowlist.
