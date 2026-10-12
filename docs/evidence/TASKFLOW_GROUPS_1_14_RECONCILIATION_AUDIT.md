# TaskFlow Groups 1–14 Reconciliation Audit

**Status:** REVIEWED AGAINST CANONICAL SPECIFICATION AND ACCEPTANCE SUITE / IMPLEMENTATION AND GENERATION REMAIN BLOCKED  
**Branch:** `review/taskflow-group-1-kimityr-clean`  
**Scope:** Canonical TaskFlow problem, acceptance suite, 15 semantic groups, reviewer decision records, and existing compiler-carrier/qualification audits.

## Executive result

The canonical TaskFlow specification and acceptance suite are mutually consistent at the top level. The 14 reviewer decision groups cover the 15 required semantic fields: Group 2 covers both workspace scope and role permissions. The decisions add concrete behavioral constraints to the broad problem statement; they do not authorize implementation promotion, generation, or certification.

**Disposition:**
- Canonical problem and acceptance suite alignment: **PASS — structural scope alignment only**
- Decision-record coverage of 15 semantic groups: **PASS WITH RECORD-FORMAT / PROVENANCE GAPS**
- Contradictions requiring a reviewer to reverse an approved decision: **NONE IDENTIFIED in this bounded review**
- Unresolved implementation-level details: **BLOCKED**
- Typed semantic completeness and downstream consumption: **BLOCKED**
- Trusted reviewer evidence / cryptographic envelope: **BLOCKED**
- Compiler A/B qualification: **BLOCKED**
- TaskFlow generation and runtime certification: **NOT AUTHORIZED / NOT RUN**

This audit does not claim the generated application exists or that implementation tests passed.

## Canonical sources reviewed

- `experiments/taskflow-native/PROBLEM.md`
- `golden-projects/taskflow/ACCEPTANCE.json`
- `docs/evidence/TASKFLOW_COMPILER_SEMANTIC_CARRIER_AUDIT.md`
- `docs/evidence/COMPILER_PATH_QUALIFICATION_INVENTORY.md`
- `docs/evidence/COMPARATIVE_COMPILER_EVALUATION_PROTOCOL.md`
- Reviewer decision records Groups 1–14 under `docs/evidence/taskflow_review/`

The canonical acceptance suite requires authentication, workspace tenancy, RBAC, projects, tasks, comments, activity history, search/filter, dashboard, audit trail, and operational observability. It also requires requirements traceability, API contract, security, unit/integration/contract/E2E/regression tests, build, deployment smoke, runtime observation, and an evidence manifest. Eight explicit negative cases must be covered. The acceptance rule disallows certification based on theatrical, unverified, or simulated-only capability.

## Decision coverage matrix

| Semantic group | Decision record | Reconciled scope | Audit status |
|---|---|---|---|
| 1. `identity.registration_and_authentication` | Group 1 | Registration, credential verification/reset, MFA, authentication failures | **Covered; implementation details still require typed representation** |
| 2. `authorization.workspace_membership_scope` | Group 2 | Workspace isolation and current membership checks | **Covered; require per-operation enforcement proof** |
| 3. `authorization.owner_manager_member_permissions` | Group 2 | Owner/manager/member role-action boundaries and fail-closed denial | **Covered; exact operation/action matrix must be machine-readable** |
| 4. `data.workspace_project_task_relationships` | Group 3 | Workspace ownership, project/task relationships, moves, assignee validity | **Covered; atomic constraints and negative cases need typed carriers** |
| 5. `data.comments_and_activity_history` | Group 4 | Comment permissions, immutable history, audit payload and retention | **Covered; sensitive-event access and retention policy need explicit implementation mapping** |
| 6. `tasks.assignment_status_priority_and_due_dates` | Group 5 | Statuses/transitions, priorities, timezone-aware due dates, assignment | **Covered; transition graph and date policy need strict typed values** |
| 7. `tasks.archive_visibility` | Group 6 | Archive/restore, active-view filtering, task/project archive interaction | **Covered; query-wide behavior requires consumer tests** |
| 8. `sessions.revocation_and_expiry` | Group 7 | Absolute/idle expiry, effective revocation, session and membership changes | **Covered at decision level; durations/bounds and lifecycle model remain unresolved** |
| 9. `api.request_response_and_error_contracts` | Group 8 | REST/JSON, response/error shapes, pagination, validation, idempotency contract | **Covered; endpoint schemas and compatibility policy must be concretely encoded** |
| 10. `frontend.required_interactions_and_state_transitions` | Group 9 | Screens, workspace switching, pending/error states, role-aware UI, archive behavior | **Covered at decision level; first-class UI state model remains a carrier gap** |
| 11. `persistence.consistency_and_atomic_mutations` | Group 10 | Atomic multi-record mutations, rollback, concurrency, durable recovery | **Covered; per-mutation transaction boundaries and durability promise must be encoded** |
| 12. `operations.idempotency_and_unique_effect_identity` | Group 11 | Key scope/reuse, retries, concurrency, unique effect/audit identity | **Covered; per-operation declarations, retention and recovery need typed contracts** |
| 13. `operations.health_readiness_and_audit_evidence` | Group 12 | Health vs readiness, safe telemetry, audit durability and evidence status | **Covered; health predicates and evidence manifest bindings remain to implement** |
| 14. `deployment.reproducible_execution_environment` | Group 13 | Dependency/build reproducibility, secrets, persistence, environment parity, recovery | **Covered; generic record schema/provenance needs normalization** |
| 15. `verification.required_capability_and_negative_case_mapping` | Group 14 | Traceability, test/evidence type separation, negative cases, honest statuses | **Covered; no current proof of complete artifact-to-test mappings** |

## Acceptance-suite reconciliation

| Acceptance requirement | Decision group(s) | Required independent evidence | Current disposition |
|---|---|---|---|
| Authentication | 1, 7, 8 | Registration/login/MFA/reset tests; invalid-auth and expiry/revocation tests | **BLOCKED — no TaskFlow runtime evidence established here** |
| Workspace tenancy | 2, 3, 6, 7 | Cross-workspace read/write, workspace-switch/cache and membership-revocation tests | **BLOCKED** |
| RBAC | 2, 3, 6, 8 | Role-action matrix, unauthorized role mutation, owner-only operation tests | **BLOCKED** |
| Projects | 3, 6, 10 | Relationship, archive/restore, atomicity and persistence tests | **BLOCKED** |
| Tasks | 3, 5, 6, 10, 11 | Assignment, transition, date validation, move, retry and rollback tests | **BLOCKED** |
| Comments | 4, 8, 10, 11 | Author/moderator authorization, deletion audit, idempotency and atomicity tests | **BLOCKED** |
| Activity history | 4, 10, 11, 12 | Unique event identity, mutation consistency, immutability and safe payload tests | **BLOCKED** |
| Search/filter | 6, 8, 9 | Workspace-scoped filters, archive visibility, pagination and UI tests | **BLOCKED** |
| Dashboard | 6, 9, 12 | Authorized, archive-aware aggregates and runtime/UI tests | **BLOCKED** |
| Audit trail | 4, 10, 11, 12, 14 | Audit-event consistency, secret scrubbing, durability and independent evidence manifest | **BLOCKED** |
| Operational observability | 12, 13, 14 | Health/readiness dependency tests, structured logs, restart/recovery and deployment smoke | **BLOCKED** |

The eight canonical negative cases are all covered at decision level:
- `cross_workspace_read`: Groups 2, 3, 6, 8, 9
- `cross_workspace_write`: Groups 2, 3, 8, 10
- `unauthorized_role_mutation`: Groups 2, 8, 9
- `foreign_project_task`: Groups 3, 8, 10
- `foreign_workspace_assignee`: Groups 3, 5, 10
- `duplicate_idempotent_effect`: Groups 8, 10, 11, 12
- `invalid_authentication`: Groups 1, 7, 8
- `expired_or_revoked_session`: Groups 1, 7, 8, 9

This mapping establishes decision coverage only. The implementation/test/artifact columns remain unpopulated until independently verified evidence is available.

## Findings and gaps

### F1 — Approval records are not yet one normalized, machine-verifiable ledger

Groups 1–12 use the earlier `tiannara.taskflow.reviewer-decision.chat-record.v1` style; Groups 13–14 use a different shape with `record_id`, `status`, and nested `decision`. A single downstream consumer cannot safely assume the same schema or field names across all 14 files. Group 2's actual filename is `group_2_workspace_authorization.kimityr.json`; references must use this exact path.

**Required:** define a versioned canonical decision-ledger schema and deterministic normalization/validation for all 14 records. Preserve original files and original approval wording/provenance; do not silently rewrite chat approval into a cryptographic signature.

### F2 — Chat approval is not trusted cryptographic evidence

All records represent conversation approvals only. No signing key, trusted reviewer envelope, or independently verified signature is established by this audit. A reviewer ID string is not proof of signer identity.

**Required:** use the existing trusted-evidence mechanism with externally provisioned trust material, bind the envelope to the exact canonical problem/acceptance hashes, graph ID/hash, normalized decision ledger and resolution-record digest, and verify it independently. Do not place signing keys in the repository or reports. If the trust key/envelope is unavailable, remain blocked.

### F3 — Decisions are not yet strict semantic values

The semantic-carrier audit says the current shape gate only checks minimum structure; extension dictionaries/descriptions are not proof of consumption. Important values still need domain-specific types and explicit constraints, including:
- authentication and credential/session lifecycle;
- complete role-action/deny matrix;
- relationship and task-move invariants;
- workflow transition graph and due-date/time-zone policy;
- archive visibility on every list/search/dashboard/direct endpoint;
- API schemas/error/pagination/idempotency behavior;
- frontend screens and loading/empty/error/session/workspace state transitions;
- transaction boundaries, rollback and concurrency;
- audit schema/retention and health/readiness predicates;
- deployment reproducibility and evidence trace links.

Group 7 intentionally does not set numeric idle/absolute expiry durations or allowed bounds. These must be resolved and encoded before deployment qualification; do not invent values in an adapter.

### F4 — Two compiler paths are candidates, not qualified compilers for this input

The inventory identifies Cap-C `ProjectCompiler` and `constitutional_architecture.compiler.pipeline.CompilerPipeline` as the strongest candidates, but they consume different models and semantic equivalence/consumer bindings are unproven. Python/FastAPI vs Go output from one pipeline is a cross-target lowering experiment, not two independent end-to-end compilers.

**Required:** normalized trusted inputs, two deterministic adapters, source-level consumer tracing, mutation/omission negative tests, then independent compiler qualification. Until all required gates pass, no TaskFlow A/B generation.

### F5 — Acceptance evidence remains absent/unverified

The canonical suite requires build, deployment smoke, live runtime observation, all test classes and evidence manifest. The current design/audit documents explicitly do not establish those results.

**Required:** each acceptance item must have stable requirement ID, native typed semantic path, generated artifact path/hash, test ID/command, execution result, evidence type, timestamp/environment, and evidence digest. Missing or simulated evidence must remain UNKNOWN/BLOCKED and cannot be promoted to PASS.

### F6 — Scope and security policy additions are not contradictions, but need explicit implementation treatment

Group 1 adds mandatory MFA and email verification before workspace access beyond the short canonical summary; this is a stricter interpretation of authentication, not a contradiction. Group 4's permanent comment deletion must preserve a separate durable audit event without retaining deleted comment text. Group 6 requires independent task archive state to survive project restoration. Group 7 requires revocation effective across request paths/instances. These are required semantics and must not be dropped as optional implementation details.

## Required next implementation sequence

1. **Completed on the review branch:** normalize the 14 decision records into `docs/evidence/taskflow_review/decision_ledger.v1.json`, preserving originals and explicitly retaining chat-only trust status.
2. **Validator added; execution awaits CI confirmation:** `experiments/taskflow-native/validate_decision_ledger.py` checks canonical Git blob hashes, original-record blob hashes, all 15 unique semantic IDs, 14 unique groups, all 11 capabilities, 12 quality gates, 8 negative cases, and fail-closed authorization/certification flags. `tests/test_taskflow_decision_ledger_validation.py` adds standard-suite tests including a deliberate duplicate-mapping failure. This validates consistency/coverage only, not semantic compiler consumption or application behavior.
3. **Resolve implementation blockers without guessing:** specifically session expiry bounds, remaining deletion/membership dependency policies, and any per-operation idempotency/pagination/API details that require implementation-level choices or explicit reviewer resolution.
4. **Upgrade the shape gate to strict domain-specific models** and field-level traceability. Unsupported values and missing fields must block construction.
5. **Create deterministic adapters for both compiler candidates** from the same frozen spec, acceptance suite, and trusted ledger; publish exact field-to-native-carrier and consumer bindings.
6. **Add omission/weakening tests:** remove or weaken each semantic field in turn and prove adapter construction or downstream verification fails.
7. **Qualify the compiler pair** independently. Do not run the two application generations before this gate is all PASS.
8. **Run the two isolated TaskFlow generations**, if and only if generation authorization is separately granted and the trusted/semantic/compiler gates pass. Preserve untouched artifacts and execute the same independent acceptance suite.
9. **Keep ReadingShelf deferred** until TaskFlow's execution and evidence boundaries are sound.

## Final disposition

**Decision coverage:** ACCEPTED AT CHAT-REVIEW LEVEL.  
**Semantic completeness:** BLOCKED.  
**Trusted review envelope:** BLOCKED.  
**Compiler pair qualification:** BLOCKED.  
**TaskFlow generation:** NOT AUTHORIZED / NOT RUN.  
**Certification:** NOT CERTIFIED.

The approval records define requirements; they do not prove implementation or runtime behavior.


## Mechanical validation follow-up (2026-10-12)

The review branch now includes a fail-closed validator at `experiments/taskflow-native/validate_decision_ledger.py` and standard-suite tests at `tests/test_taskflow_decision_ledger_validation.py`. The validator recomputes Git blob object IDs for the canonical problem, acceptance suite, and all 14 original reviewer records; checks that ledger and matrix coverage are complete and duplicate-free; compares capabilities, quality gates, and negative cases to the acceptance suite; and rejects any change that upgrades chat records to trusted attestations or marks generation/certification as authorized.

The test and validator changes have been committed, but CI for the latest head has not yet completed. Therefore validator execution is **PENDING CI**, not PASS. Even if it passes, the result establishes record integrity and coverage only. It does not resolve the outstanding session-expiry bounds, role/action and deletion edge cases, trusted envelope, typed carrier/consumer binding, compiler-pair qualification, or runtime acceptance evidence. Generation remains **NOT AUTHORIZED / NOT RUN**.


## Explicit unresolved-decision docket

The 12 implementation-level questions identified during reconciliation are now tracked in `docs/evidence/taskflow_review/OPEN_IMPLEMENTATION_DECISIONS.v1.md`. They cover session lifetime bounds; exact role/action permissions; project/task deletion versus archive; workspace deletion with dependent data; membership-removal dependencies; MFA recovery; API pagination/versioning; idempotency retention and conflict behavior; audit retention/access; comment deletion rights; date/time semantics; and stable conflict responses. No defaults have been inferred. Each item must be explicitly resolved, typed, traced to a consumer, and tested before the corresponding gate can pass.


## Typed semantic gate regression tests (2026-10-13)

Added `tests/test_taskflow_semantic_contract_gate.py` with cases for a structurally complete fixture, a missing required key, a placeholder value, a scalar payload, and a non-authoritative field set. These tests exercise the existing shape validator; they do **not** prove the values are semantically correct, originate from trusted reviewer decisions, are consumed by either compiler, or generate correct artifacts. The production TaskFlow path still explicitly documents that its guarded typed-ISR transition is not wired into all production compiler/backend entry boundaries. The new tests await CI on the new commit.


## Production intent-compiler boundary hardening (2026-10-13)

The gate-enabled `IntentCompiler.compile_full` path now calls `validate_taskflow_semantic_contract` immediately after graph-bound resolution checks and before invoking the TaskFlow semantic projector. This closes a gap where a complete field index could be graph-bound but still contain scalar, missing-key, or placeholder payloads. The change does not claim semantic correctness or backend consumption: the projection contract still preserves values in `SystemModel.extensions`, which is provenance/carriage rather than proof of implementation. CI for this change is pending.
