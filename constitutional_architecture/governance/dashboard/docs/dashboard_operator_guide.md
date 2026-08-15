# Governance Dashboard — Operator Guide

Phase 28 · Milestone 5A · `governance/dashboard/`

The Governance Dashboard is a **thin, server-rendered web console** (BFF)
over the Governance Kernel. Operators use it to see what is governed, what
was decided and why, who approved what, how actions are traced, and to take
the few human decisions the platform requires (approvals, exception
revocation, audit verification).

The Governance Kernel remains the **single source of truth**. The dashboard
never writes state itself; every mutation it makes goes through kernel APIs
and is audit-recorded.

---

## 1. Quick start (demo mode)

```powershell
python -m uvicorn "constitutional_architecture.governance.dashboard.app:demo_app" --factory --port 8080
```

Open <http://localhost:8080> and log in with a demo user:

| User | Password | Roles |
|------|----------|-------|
| `alice` | `alice-pw` | auditor + operator |
| `bob`   | `bob-pw`   | governance viewer |
| `carol` | `carol-pw` | approver |
| `dave`  | `dave-pw`  | admin |

> Demo users are for local exploration only. In production the `users` map
> in `dashboard/config.py` is replaced by your identity provider (OIDC);
> roles and permissions stay declarative.

## 2. What you can do

| Page | Route | What it answers |
|------|-------|-----------------|
| Health | `/` | Is governance healthy? Audit chain valid? Anything expiring? |
| Constitutions | `/constitutions` | What is the root law? Which constitution is active? |
| Policy sets | `/policy-sets` | Which rule packs are active and what do they require? |
| Evaluations | `/evaluations` | What decisions were made and why? |
| Decision reconstruction | `/evaluations/{id}/reconstruct` | Full dossier: request, decision, policy evaluations, evidence, approvals, exceptions, audit events, lineage |
| Approvals | `/approvals` | What is waiting for human approval? Approve or reject. |
| Exceptions | `/exceptions` | Active/revoked deviations from policy. Revoke when resolved. |
| Audit log | `/audit` | Every significant action, hash-chained. |
| Audit integrity | `/audit/integrity` | Is the chain intact? Which event broke it? |
| Lineage | `/lineage` | Forward/backward traceability of changes. |
| Metrics | `/metrics` | Page views, API errors, kernel request duration, action counters. |

## 3. Human decisions

### 3.1 Approve / reject a pending approval
1. Open **Approvals**; filter `PENDING`.
2. Open the approval; read the decision summary, evidence, constraints.
3. Enter a comment and choose **Approve** or **Reject**.

The decision is recorded on the kernel, appears in the audit log
(`APPROVAL_DECIDED`), and the approval leaves the pending queue. The final
action decision (ALLOW/DENY) is produced by the orchestrator (PEP) once all
required approvals are decided.

### 3.2 Revoke an exception
1. Open **Exceptions**; filter `ACTIVE`.
2. Open the exception; read the justification and scope.
3. Enter a revocation justification and confirm **Revoke**.

Revocation is immediate and audit-recorded
(`EXCEPTION_REVOKED` / `EXCEPTION_REVOKE_AUDITED`).

### 3.3 Re-verify the audit chain
1. Open **Audit Integrity**.
2. Click **Re-verify chain**.

The page reports `VALID` or the first broken event (index, hash, previous
hash) for incident investigation.

## 4. Health checks

| Endpoint | Meaning |
|----------|---------|
| `/health/live` | The process is up. |
| `/health/ready` | Kernel, auth, templates, and static assets are all functional. |

`/health/ready` returns `not_ready` (HTTP 503) when the kernel is
unreachable.

## 5. Incident handling

- **Any page shows "Governance kernel unavailable" (503):** the dashboard
  has failed closed — nothing can be displayed or executed. Check that the
  kernel is running; the dashboard will recover without state loss because
  all state lives in the kernel.
- **Audit Integrity shows `BROKEN`:** the hash chain has been tampered with.
  The page shows the first invalid event. Preserve the evidence, do not
  modify kernel state, and involve the security/audit team. A chain can only
  be "repaired" by restoring the kernel from an untampered source — never by
  editing events.
- **An action you expected is missing:** use Decision Reconstruction on the
  decision ID; the dossier shows every step the policy engine took.

## 6. Operations checklist

- Log in with least-privilege roles (viewers never mutate).
- Never expose `/health/*` or `/metrics` without session protection in front
  of a monitoring stack that can authenticate.
- Rotate demo users before any non-local deployment (`config.py`).
- Monitor `/metrics`:
  - `dashboard_api_errors_total` rising → investigate.
  - `dashboard_approval_actions_total` / `dashboard_exception_revocations_total`
    → the human decision workload (audit trail).
