# TaskFlow Native SystemModel Gap Matrix

Date: 2026-10-11
Scope: static comparison of the canonical TaskFlow problem/acceptance snapshot with the native `SystemModel` schema.
Verdict: **BLOCKED before typed ISR creation.** This is a specification gap analysis, not implementation or certification evidence.

## Evidence already represented by the adapter

The provider-free adapter creates a deterministic native `RequirementGraph` from only the snapshot's `PROBLEM.md` and `ACCEPTANCE.json`. Its graph has stable IDs, source pointers, and explicit edges for the 15 listed security/correctness and operational obligations. Capability/gate/negative-case evidence stays UNKNOWN. It deliberately returns neither a `SystemModel` nor a typed ISR.

## Required semantics that remain absent or under-specified

| Area | What the canonical contract says | What is still missing before a safe native model can be built |
|---|---|---|
| Domain entities | Workspaces, users, projects, tasks, comments, activity history are implied or named | Canonical entity IDs/names, fields, requiredness, constraints, ownership, lifecycle and archive representation |
| Relationships | Workspace membership, task/project/workspace consistency, assignee membership | Cardinality, deletion behavior, foreign-key/invariant rules, reassignment semantics, cross-workspace relationship handling |
| Roles and permissions | Owner/manager/member roles; owner-only operations; fail-closed authorization | Complete role × operation matrix, workspace creation/transfer rules, manager privileges, membership changes and resource-specific policy |
| Authentication | Registration/authentication and session invalidation | Credential/session lifecycle, expiry, revocation, recovery/reset, and the exact invalid-session rejection contract |
| API contracts | User-visible capabilities and idempotency obligations | Operation inventory, request/response/error schemas, pagination/filter semantics, idempotency-key scope and which operations are idempotent |
| UI contracts | Multi-user task-management web app and a useful dashboard | Required screens, navigation, form validation, empty/error states, accessible interaction contracts and dashboard calculations |
| Consistency | Relationships must remain consistent; duplicate effects prohibited for declared idempotent requests | Transaction/invariant boundaries, concurrency semantics, ordering and retry behavior |
| Data protection | Cross-workspace access fails closed; audit events required | Data classification, retention, backup/restore requirements, secrets policy and explicit encryption posture where not already mandated |
| Deployment and operations | Reproducible deployment, health/readiness, structured evidence | Availability/scaling target, environments, rollout and recovery objectives, resource budgets |
| Verification | 12 enabled quality gates and 8 negative cases | Executable gate definitions, test data, exact oracles, evidence schema and independent verifier contract |

## Native schema defaults that must not be mistaken for TaskFlow intent

The current `tiannara.domain.models.system_model` schema supplies defaults including:

- authentication posture `token_based`; authorization `none`;
- data classification `internal`; encryption flags default true;
- consistency posture `strong`;
- infrastructure topology `modular_monolith`, stateless, single-zone;
- rolling deployment across development/staging/production with static scaling;
- unit, integration and end-to-end tests with enforced coverage;
- scheduled backups and restore-from-backup disaster recovery.

Some are useful general defaults, but they are not all derivable from the TaskFlow snapshot. In particular, `authorization=none` conflicts with the stated RBAC requirement, while choosing token-based authentication or a consistency/topology/deployment posture without recording that choice would be an unreviewed assumption.

The current schema also uses non-null enums and booleans for several posture fields. Simply putting `"UNKNOWN"` in `extensions` is not sufficient if the compiler continues consuming the defaulted typed fields.

## Safe next change

Do not instantiate `SystemModel` until one of these has been reviewed and tested:

1. Add an explicit unresolved/unknown representation for every mandatory posture that can be unknown, preserving old payload validation and existing serialized/hash behavior; or
2. Introduce a separate, typed pre-model resolution record and a mandatory gate that prevents model construction until all compiler-consumed fields are resolved.

The choice must be backed by schema compatibility tests, legacy payload round-trip/hash tests, and tests proving unresolved values cannot pass backend selection. No enum extension or default change is authorized by this audit alone.

## Gate status

- Snapshot integrity and provider-free analysis: previously verified by the dedicated provider-free workflow.
- Native requirement graph and fail-closed boundary: PASS in [TaskFlow Native Adapter run 38123979393](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38123979393).
- Typed SystemModel construction: BLOCKED.
- Application generation: NOT RUN by this adapter.
- Build/API/UI/runtime/security/persistence/traceability certification: UNKNOWN.
