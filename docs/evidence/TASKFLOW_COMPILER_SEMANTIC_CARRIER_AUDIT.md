# TaskFlow Semantic Carrier Coverage Audit

Status: **DESIGN AUDIT / ADAPTERS NOT IMPLEMENTED / GENERATION BLOCKED**

## Purpose

This audit checks whether the two candidate compiler input models have explicit, structurally appropriate carriers for the 15 compiler-owned TaskFlow semantic fields. It is not a mapping implementation and does not resolve reviewer decisions. A field's presence in free-form descriptions or an extension dictionary is not accepted as proof that downstream code generation consumes it.

Candidate A is Cap-C `SystemModel` via `ProjectCompiler`; candidate B is `constitutional_architecture.isr.model.isr.ISR` containing a `System` tree, consumed by `CompilerPipeline`.

## Field-by-field carrier assessment

| Mandatory field | Cap-C `SystemModel` candidate carrier | Constitutional ISR candidate carrier | Assessment / required proof |
|---|---|---|---|
| `identity.registration_and_authentication` | `security.authentication`; API/service operations; no first-class registration or credential lifecycle model | `Policy` with `PolicyType.AUTHENTICATION`; `Service`/`Operation`; no first-class credential lifecycle primitive shown | **PARTIAL** — must define registration fields, credential/session lifecycle and invalid-auth behavior; prove emitted handlers enforce them |
| `authorization.workspace_membership_scope` | `security.authorization`; `DataModelSpec.invariants`; service/API operation descriptions | `Policy` / `Permission` with resources/actions/conditions; `Entity` relationships; requirement constraints | **PARTIAL** — needs explicit workspace scoping across every protected read/write and negative-case links, not a global RBAC label |
| `authorization.owner_manager_member_permissions` | `security.authorization` is only a model-level choice; no typed role-action matrix in the inspected model | `Policy.roles`, `Policy.rules`, `Permission.actions`, `Permission.conditions` are plausible native carriers | **PARTIAL** — exact action-by-role decisions and deny semantics must be reviewed and traced into authorization enforcement |
| `data.workspace_project_task_relationships` | `DataModelSpec.fields` and `invariants`; relationship semantics have no dedicated first-class relation type in this model | `Entity.fields`, `Relationship`, `Constraint`; relationship target identity can be represented structurally | **PARTIAL** — exact foreign-key/ownership invariants, move rules and cross-workspace negative cases need explicit typed representation |
| `data.comments_and_activity_history` | `DataModelSpec`, `EventSpec`, service/API operations | `Entity`, `Event`, `Service` operations and event declarations | **PARTIAL** — comment edit/delete rules and audit event payload/actor/time requirements are unresolved; generic event presence is insufficient |
| `tasks.assignment_status_priority_and_due_dates` | `DataModelSpec`, service/API operations, capability/requirement links | `Entity` fields/constraints, `Workflow` states/transitions, `Service` operations | **PARTIAL** — allowed status/priority values, transition guards, due-date timezone/validation and workspace-bound assignee need typed decisions |
| `tasks.archive_visibility` | Data-model invariants and service/API query descriptions; no first-class archive visibility contract shown | Entity fields/constraints and service operations; no dedicated archive visibility construct shown | **GAP / PARTIAL** — archive/restore/deletion and default-query visibility must be explicit and tested, not inferred from a boolean field |
| `sessions.revocation_and_expiry` | `security.authentication` but no first-class session state, revocation or expiry contract shown | Authentication policy and service operations; no first-class session lifecycle carrier shown in the inspected core models | **GAP** — requires explicit session lifecycle state/transition, expiry and concurrent-revocation semantics |
| `api.request_response_and_error_contracts` | `ApiSpec` / `ApiOperation` provide names and operation semantics, but not complete request/response schemas or error envelopes | `Interface` / `Endpoint` and `Service.Operation` input/output `Field` tuples are candidate carriers | **PARTIAL** — full request/response schema, validation and error contract must be represented and verified per operation |
| `frontend.required_interactions_and_state_transitions` | No first-class frontend screen/state-transition model is apparent in `SystemModel`; generic capabilities/services do not suffice | `Workflow` can represent domain workflows but is not equivalent to user-interface screens, loading/empty/error states or navigation | **GAP** — define a technology-neutral interaction model or explicitly block qualification until equivalent semantics are representable |
| `persistence.consistency_and_atomic_mutations` | `DataModelSpec.consistency` and `invariants` exist; no explicit per-mutation transaction/rollback contract shown | `Entity` relationships/constraints and migration semantics exist; no complete per-operation atomicity contract shown in inspected core types | **PARTIAL** — identify each multi-record mutation, atomic boundary, rollback behavior and evidence checks |
| `operations.idempotency_and_unique_effect_identity` | `ApiOperation.idempotent` exists; no explicit unique effect identity/retention contract shown | `Service.Operation.is_idempotent`, operation metadata, events and constraints are candidate carriers | **PARTIAL** — define idempotency key scope, duplicate-effect semantics and auditable effect identity; test retries and concurrent duplicates |
| `operations.health_readiness_and_audit_evidence` | `OperationalPolicies.observability_requirements`, service-level objectives, and security audit flag | Operational policies, health-related interfaces/operations, audit `Event`/`Policy` and `TestingAnchor` | **PARTIAL** — exact health/readiness conditions, safe disclosure and mandatory audit evidence schema remain to be bound |
| `deployment.reproducible_execution_environment` | `DeploymentModel` holds rollout/environment/scaling posture, but not a complete pinned reproducibility contract | `Deployment` / `DeploymentIntent` and constraints are candidate carriers | **PARTIAL** — decide and encode required lockfiles, runtime inputs, reproducible build checks and environment parity without prescribing a compiler-specific stack |
| `verification.required_capability_and_negative_case_mapping` | `TestingPolicy`, capabilities, requirement graph and acceptance criteria references | `System.requirements`, `acceptance_criteria`, `testing_anchors`, `SecurityThreat` and subject refs | **PARTIAL** — every capability and negative case needs stable IDs, explicit artifact/test bindings, and independent live evidence; declarations alone cannot certify |

## Cross-cutting findings

1. **The models are not semantically equivalent yet.** Candidate A has useful typed security, data, API, deployment, testing and operational fields. Candidate B has richer entity relationships, permissions, operations and workflows. Neither inspected model alone provides every TaskFlow contract as a first-class, verified semantic.
2. **Extensions and metadata are not a substitute for consumption.** Putting the original values in `SystemModel.extensions`, `Module.metadata`, or descriptions can preserve data, but it does not prove that a backend implements the obligation. Such carriers may be used as provenance only unless a consumer is independently traced and tested.
3. **Compiler B's validation pass had a degraded success path; a fail-closed correction is now committed.** `constitutional_architecture/compiler/passes/validation_pass.py` previously logged validation exceptions as “assuming valid” and returned success. The implementation now emits an error and returns `success=False` if validation throws or reports invalid architecture. Focused regression tests cover validator exceptions, invalid results and valid results; they are awaiting the newest CI run.
4. **Compiler A's bundle verification is not TaskFlow acceptance verification.** `ProjectCompiler` runs a backend build-profile verifier and documentation validation. Those checks do not by themselves prove workspace isolation, role matrix, session revocation, atomic mutations, frontend transitions, or negative-case behavior.
5. **Do not fill missing semantics with defaults.** The canonical review template intentionally has unresolved decisions. No adapter should infer role permissions, session rules, UI flows, transaction boundaries or API error contracts to make a pipeline compile.

## Required next gates

1. Complete trusted review of the 15-field ledger and verify the graph/snapshot-bound evidence envelope.
2. Design a technology-neutral semantic carrier for currently missing contracts (especially session lifecycle and frontend interaction/state transitions), with explicit schema versioning and field-level traceability.
3. Implement separate deterministic adapters for the two candidate input models. Each adapter must reject unresolved/unsupported values, emit a field-to-native-carrier map, and preserve exact source/value digests.
4. Add negative tests proving that deleting or weakening any required semantic blocks adapter construction or fails a downstream behavior test.
5. Audit actual consumers/pass implementations, including Compiler B validation's degraded exception behavior. Do not treat the `CompilationResult.verification` summary as proof of TaskFlow behavior.
6. Only then qualify the pair and begin the two isolated application generations.

## Disposition

- Shared semantic input: **NOT ESTABLISHED**.
- Candidate A/B adapter parity: **BLOCKED**.
- Compiler pair: **NOT QUALIFIED**.
- TaskFlow generation iterations A and B: **NOT RUN**.
- This document is a source-model audit, not execution or certification evidence.