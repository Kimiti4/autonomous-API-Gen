# Phase 28 — Constitutional Governance: Governance Kernel Specification v0.1

**Status:** Ratified for implementation · **Scope:** Governance Kernel v0.1 (Sprint 1)
**Repository location:** `constitutional_architecture/governance/`

> Phase 28 is the **constitutional control plane** for the platform. It is
> implemented first because every later phase (self-evolution, learning,
> autonomous organizations, marketplaces, distributed evolution, product
> generation) introduces a dangerous capability if left ungoverned.

---

## 1. Enforcement Guarantees

| # | Guarantee | Enforcement point |
|---|-----------|-------------------|
| 1 | Every significant action is governed by explicit policy | `ComplianceEngine.evaluate` |
| 2 | Every architectural change is versioned and attributable | `ConstitutionManager` / `PolicySetManager` (immutable hashes) |
| 3 | Every autonomous action operates within delegated authority | pack_004 `no_self_authority_expansion` |
| 4 | Every promotion requires verification and approval | pack_003 (evidence) + pack_006 (approval) |
| 5 | Every change is auditable and reconstructable | `AuditFramework.reconstruct` |
| 6 | Every approved change has a rollback path | pack_002 `*_requires_rollback_plan` |
| 7 | Every policy violation blocks execution by default | DENY override + fail-closed resolve |
| 8 | Every exception is explicit, bounded, time-limited, revocable | `GovernanceExceptionManager` |

## 2. Core Concepts

- **Constitution** — highest-level governance object: invariants, policy
  domains, approval requirements, exception policy. Machine-referenceable,
  content-hashed, versioned (statuses DRAFT → UNDER_REVIEW → ACTIVE →
  DEPRECATED/REVOKED).
- **Policy Set** — collection of enforceable rules bound to a constitution;
  immutable once activated.
- **Policy Rule** — single enforceable constraint: effect, subject_types,
  actions, conditions, required evidence/approvals, constraints, priority.
- **Governance Subject / Action** — what is governed and what it attempts
  (e.g. `ISR_REVISION` / `PROMOTE_ISR_REVISION`).
- **Policy Decision** — ALLOW | DENY | REQUIRE_APPROVAL | REQUIRE_EVIDENCE |
  ALLOW_WITH_CONSTRAINTS, always with an explanation.
- **Approval Workflow** — who/what must approve; timeouts default to
  DENY_ON_TIMEOUT; autonomous approval only inside bounded scopes.
- **Audit Evidence** — policy evaluations, approvals, evidence refs, actor,
  timestamps, constitution + policy set versions.
- **Change Lineage** — forward/backward traceability between artifacts,
  decisions, approvals, rollback plans.
- **Governance Exception** — bounded, time-limited, revocable deviation;
  never permanent by default.

## 3. Governance Kernel Architecture

```
Client Systems ──▶ Governance API ──▶ Policy Engine (PDP)
                          │                │
                          v                v
                   Approval Workflow   Policy Compiler
                          │
                          v
                   Audit Event Store (hash-chained, append-only)
                          │
                          v
                   Lineage Repository
```

- **Policy Enforcement Point (PEP):** the platform component that asks
  "is this action allowed?" before acting (Evolution Engine, Compiler,
  Marketplace, Organization Runtime, Product Factory).
- **Policy Decision Point (PDP):** this kernel. Evaluates subject, action,
  context, policies, evidence, approvals, exceptions.

## 4. Evaluation Semantics (fail closed, deterministic)

1. Rules match on `(subject_type, action)` from **ACTIVE** policy sets only
   (DRAFT sets are never evaluated).
2. Rules are evaluated in `(priority, id)` order — deterministic.
3. Conditions resolve dotted paths: `actor.*`, `context.*`, `subject.*`;
   values may reference other request fields (`context.target_agent_id`).
4. **Any matched DENY overrides everything → DENY** (reason aggregates all
   matching deny rules).
5. Else missing required evidence → `REQUIRE_EVIDENCE`.
6. Else unsatisfied required approval → `REQUIRE_APPROVAL`.
7. Else constraints present → `ALLOW_WITH_CONSTRAINTS`.
8. Else → `ALLOW`.
9. Active, unexpired, unrevoked exceptions whose scope covers the request
   suppress matched DENY rules and are listed in `exceptions_applied`.

## 5. Data Model

Implemented in `governance/schemas.py` (pydantic):

- `ConstitutionISR`, `Invariant`, `ExceptionPolicy`
- `PolicySetISR`, `PolicyRule`, `Condition`, `ApprovalRequirement`, `Constraint`
- `Actor`, `GovernanceEvaluationRequest`
- `GovernanceDecision`, `PolicyEvaluation`
- `ApprovalRecord`, `AuditEvent`
- `ChangeLineage`, `GovernanceException`, `ExceptionScope`

All content hashes: `sha256(json.dumps(payload, sort_keys=True))`.

## 6. API Contract

`governance/api/openapi.yaml` — OpenAPI 3.0.3, v0.1 endpoints:

```
POST /v1/constitutions                 GET  /v1/constitutions/{id}
POST /v1/constitutions/{id}/activate
POST /v1/policy-sets                   GET  /v1/policy-sets/{id}
POST /v1/policy-sets/{id}/activate
POST /v1/governance/evaluate
POST /v1/approvals                     POST /v1/approvals/{id}/decision
POST /v1/audit/events                  GET  /v1/audit/events
GET  /v1/audit/reconstruct/{decision_id}
```

## 7. Initial Policy Packs (001–006)

`governance/default_policies.py`:

| Pack | Rules |
|------|-------|
| 001 ISR Integrity | `isr_revision_requires_parent_hash`, `isr_revision_requires_content_hash` (DENY) |
| 002 Reversibility | `promotion_requires_rollback_plan`, `isr_promotion_requires_rollback_plan` (DENY) |
| 003 Verification | `high_impact_change_requires_verification` (REQUIRE_EVIDENCE), `isr_promotion_requires_verification` (DENY) |
| 004 Autonomous Authority | `no_self_authority_expansion` (DENY — actor == target) |
| 005 Auditability | `action_requires_audit_commitment` (DENY) |
| 006 Approvals | `high_impact_change_requires_architecture_review` (REQUIRE_APPROVAL, ROLE architecture_reviewer, DENY_ON_TIMEOUT) |

## 8. Acceptance Tests

`tests/test_governance_kernel.py` (30 tests, all green):

1. **A1 — Deny Unsafe ISR Promotion**: no rollback plan + no verification →
   `DENY`, reason aggregates the denying rules.
2. **A2 — Require Approval for High-Risk Change**: evidence present, policy
   requires architecture review → `REQUIRE_APPROVAL` with
   `architecture_reviewer`.
3. **A3 — Allow After Approval**: all required approvals APPROVED →
   `ALLOW`; an `ACTION_FINALIZED` audit event is recorded.

Plus: rejection blocks (`DENY`), timeout denies by default, tamper-evident
hash chain, decision reconstruction, lineage forward/backward, exception
boundedness/scope/revocation/expiration, deny-overrides-allow, determinism,
constitution lifecycle, policy compiler validation.

## 9. Milestone Coverage

| Milestone | Status | Evidence |
|-----------|--------|----------|
| M0 Specification | ✅ | this document + openapi.yaml |
| M1 Constitution & Policy Mgmt | ✅ | `constitution.py`, `policy_compiler.py` |
| M2 Policy Evaluation Engine | ✅ | `compliance.py` |
| M3 Approval Workflow | ✅ | `approval_workflow.py` |
| M4 Audit & Lineage | ✅ | `audit.py`, `lineage.py` |
| M5 Exceptions & Dashboard | ✅ | `exception_manager.py`, `dashboard/` (Milestone 5A) |
| M6 PEP SDK | ✅ | `pep/` (Milestone 5B/5C, Phase 28.1) |

## 10. Definition of Done

- [x] Constitutions versioned + activated; policy sets bound + immutable when active
- [x] Actions evaluated before execution (fail closed)
- [x] High-risk actions require approval; approvals grant/reject/expire/revoke
- [x] Audit events recorded for all significant actions; hash-chained
- [x] Lineage connects artifacts to decisions; rollback refs enforced
- [x] Exceptions bounded and revocable
- [x] Decisions reconstructable; deterministic for identical inputs
- [x] Autonomous actors cannot exceed delegated authority
- [x] Governance Dashboard (Milestone 5A) — read-mostly console answering:
      what is governed / decided / why / who approved / how it is traced;
      AC-1..AC-6 covered by `tests/test_governance_dashboard.py`
- [x] PEP SDK (Milestone 5B/5C) — `pep/` module: errors, client, context
      builder, enforcer, decorators, evolution promotion guard; acceptance
      A1..A6 + fail-closed covered by `tests/test_governance_pep.py`

### Milestone 5A closure note — web dashboard (BFF)

Milestone 5A delivered the interactive FastAPI dashboard BFF in addition
to the static console:

- `governance/dashboard/` — `app.py` (30 routes), `client.py`,
  `service.py`, `auth.py`, `config.py`, `errors.py`, `view_models.py`,
  24 Jinja2 templates, static assets.
- Security: session auth on all protected routes, CSRF on all mutations
  (constant-time compare), role→permission matrix, kernel-level
  authorization for human actors (kernel denials surface as 403, never
  overridden), context redaction, fail-closed 503 on kernel
  unavailability.
- Observability: `/health/live`, `/health/ready`, session-protected
  `/metrics`.
- Acceptance: 79 tests green across 6 files
  (`governance/dashboard/tests/`) covering AC-1..AC-7 (incl. audit
  integrity verification, approval decisions audit-visible, exception
  revocation, lineage explorer, reconstruction, role matrix, CSRF,
  kernel-denial surfacing).
- Docs: `governance/dashboard/docs/{dashboard_operator_guide,
  dashboard_security,dashboard_architecture}.md`.

### Phase 28.1 closure note — evolution guard gaps closed

- `ChangeLineage.evidence_refs` — lineage now carries evidence refs
  (verification/simulation/fitness reports) end to end.
- Rollback execution — `guard_promote(..., rollback_action=...)` executes
  the rollback plan on promotion failure, records an `ACTION_ROLLED_BACK`
  hash-chained audit event, and raises `PromotionExecutionError` carrying
  the original cause, rollback outcome, and decision id. Failed
  promotions never record success lineage.
- `EnforcementResult.exceptions_applied` — decision exceptions surfaced
  on the result for waivers.
- Acceptance: `tests/test_governance_pep.py` now has 12 tests (A1..A10 +
  waiver complement + fail-closed) — all green.

### Phase 28 closure note — pre-existing collection error (non-blocking)

The package suite (406 passing) retains one pre-existing collection error in
`constitutional_architecture/tests/test_end_to_end.py`: `ImportError: cannot
import name 'Dependency' from 'constitutional_architecture.isr.model'`. It was
verified before Phase 28 work began and is unrelated to governance (no Phase
28 module imports `isr.model`). Triage: documented here; fix belongs to the
ISR module (Phase 21+ boundary); non-blocking for Phase 28 closure.

Two further pre-existing environment gaps documented in the completion
report: `pytest-asyncio` is not installed (generated-shop async tests), and
`locust` is not installed (`autonomous-api/load_test.py`). Neither touches
governance code.

## 11. Next Steps

1. **Phase 23: Enterprise Knowledge Graph** — next major phase after
   Phase 28.1.
2. **PEP integration points** — compiler, marketplace, organization
   runtime, product factory call `evaluate()` before acting (SDK ready;
   only the evolution engine seam is wired via `evolution_guard.py`).
3. **Persistence** — replace in-memory stores with append-only PostgreSQL
   (audit) + S3 artifact refs; OIDC for human actors.
4. **Stack bindings** — OpenAPI server from `openapi.yaml`; JSON Schema /
   CUE codegen for policy artifacts.
5. **Dashboard hardening** — CSRF same-site cookies, strict
   content-security-policy, audit export (JSON/CSV), approval
   finalization flow via PEP `finalize`/`confirm`.
