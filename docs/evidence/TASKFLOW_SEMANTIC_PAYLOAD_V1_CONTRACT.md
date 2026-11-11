# TaskFlow Semantic Payload v1 — implementation contract

**Disposition: PARTIALLY IMPLEMENTED / NOT APPROVED FOR GENERATION**

This document narrows the implementation target for the provider-free TaskFlow path. It does not supply reviewer decisions, resolve the open questions in the review template, or authorize compilation. The canonical problem and acceptance snapshots remain authoritative; the semantic ledger remains blocked until an authorized human resolves the gaps and the trusted evidence envelope verifies.

## 1. Boundary and invariants

The versioned payload is a technology-neutral, closed contract between the reviewed semantic-resolution ledger and the compiler's typed architectural model. It must not contain framework, language, database, cloud, hosting, or deployment-product choices.

Required invariants:

1. The payload schema version is explicit and unknown versions fail closed.
2. Exactly the compiler-owned 15 TaskFlow field paths are present. No caller-supplied subset is accepted.
3. Each field is either unresolved or has a value validated against that field's schema. Unresolved fields cannot carry values.
4. Every resolved field records its provenance. A reviewer decision additionally records rationale and an approval reference; a string that merely looks like an approval is not trusted evidence.
5. The resolution record binds to the exact graph ID/hash and immutable problem/acceptance hashes.
6. Projection is deterministic. Equal validated input and schema version must produce equal technology-neutral model content.
7. Projection must reject unknown keys, invalid references, contradictory constraints, unsupported enum values, and incomplete values. It must not fill gaps using generic synthesizer defaults.
8. Model construction and backend discovery must not occur until the semantic gate and projection validation succeed.
9. Model-carried values are provenance, not proof of implementation. Artifact derivation must declare which semantic obligations it consumes, and verification must test those obligations against the generated artifact.
10. Simulated, replayed, inferred, or unexecuted evidence cannot satisfy live-generation or runtime-certification gates.

## 2. Field payloads and minimum structural obligations

These are required schema obligations, not proposed product decisions. The field names below refine the existing TASKFLOW_MANDATORY_FIELDS contract and REQUIRED_VALUE_KEYS. A human reviewer must supply the actual values where the source snapshots do not determine them.

| Field path | Required typed payload | Validation and downstream-consumption obligation |
|---|---|---|
| identity.registration_and_authentication | registration_fields, credential_lifecycle | Registration field definitions include stable names, types, requiredness, and validation constraints. Credential lifecycle is explicit; no implicit authentication defaults. |
| authorization.workspace_membership_scope | scoped_resources, scoped_operations, cross_scope_denial | Every scoped resource/operation has a stable identifier and defined scope check; denial behavior is explicit and testable. |
| authorization.owner_manager_member_permissions | roles, action_permission_matrix | Role IDs are unique; each action has an explicit decision for every role. Missing cells are errors, not implicit allow/deny defaults. |
| data.workspace_project_task_relationships | entities, relationships, integrity_invariants | Entity/relationship references resolve; cardinality, ownership, deletion/move behavior and cross-workspace invariants are explicit. Unspecified cardinalities must remain unresolved. |
| data.comments_and_activity_history | comment_operations, activity_event_schema, visibility_rules | Allowed comment operations, event fields, actor/time semantics, and visibility are explicit. Do not assume edit/delete or retention policies. |
| tasks.assignment_status_priority_and_due_dates | status_values, priority_values, allowed_transitions, due_date_rules, assignment_rules | Enumerations are closed; transitions refer to declared values; date/time-zone and assignee-scope rules are explicit. |
| tasks.archive_visibility | archivable_resource_types, archive_restore_rules, active_query_visibility | Archival lifecycle and active-query behavior are defined for each applicable resource type. Do not infer soft-delete or restore semantics. |
| sessions.revocation_and_expiry | expiry_policy, refresh_policy, revocation_behavior | Expiry, refresh, logout/revocation, and in-flight/concurrent request semantics are explicit and testable. |
| api.request_response_and_error_contracts | operations, request_schemas, response_schemas, error_contract | Operation IDs are stable; schemas reference declared fields/types; error outcomes and validation behavior are explicit. |
| frontend.required_interactions_and_state_transitions | screens_or_views, interaction_flows, ui_state_transitions | Every required flow has defined states, events, transitions, and observable outcomes including loading/empty/error states where applicable. These are not inferred from backend routes. |
| persistence.consistency_and_atomic_mutations | consistency_guarantees, atomic_mutations, conflict_and_rollback_rules | Each multi-record mutation identifies its atomic boundary and conflict/rollback outcome. Do not select a consistency posture by default. |
| operations.idempotency_and_unique_effect_identity | idempotent_operations, key_scope_and_retention, effect_identity_rules | Idempotent operations, key scope/retention, replay response behavior, and unique effect identity are explicit. |
| operations.health_readiness_and_audit_evidence | health_conditions, readiness_conditions, audit_event_schema | Conditions and event fields are explicit; declared health or audit capabilities are not treated as implemented until observed. |
| deployment.reproducible_execution_environment | runtime_inputs, configuration_contract, reproducibility_checks | Runtime/config inputs and repeatability checks are declared without naming a technology stack. A concrete stack remains a later, separately justified lowering decision. |
| verification.required_capability_and_negative_case_mapping | capability_test_mapping, negative_case_test_mapping, evidence_requirements | Every canonical capability and negative case maps to executable checks and required evidence; missing mappings block certification. |

## 3. Schema mechanics required before implementation is considered complete

- Use strict, versioned model types for each field payload; reject extra keys.
- Use explicit enums and stable identifiers for roles, operations, entities, states, transitions, and evidence obligations.
- Validate referential integrity across the payload (e.g. transition endpoints, permission-matrix role/action IDs, relationship entity IDs, and capability/negative-case IDs).
- Keep UNRESOLVED distinct from an explicit, reviewed negative/empty value. An empty list is valid only if the reviewer has explicitly decided that the list is empty and that decision is evidenced.
- Validate the whole payload as one unit. Partial resolution must not leak into SystemModel or backend selection.
- Compute a canonical payload hash and bind it to the graph ID/hash and source snapshot hashes.
- Project to first-class, technology-neutral model structures. Keeping the whole payload only in SystemModel.extensions is insufficient.
- Return a projection report with field-by-field source path, target model path, and consumer obligations. Missing consumer mappings block compilation.
- Require mutation tests for every field: changing a resolved value must either change the corresponding typed model/consumer contract or fail closed. Tests must also prove unresolved/malformed payloads do not call the model builder, backend registry, or selector.

## 4. Current repository gaps this contract does not pretend to close

The new `TaskFlowSemanticPayloadV1` validates a versioned envelope, exact 15-field coverage, per-field required key coverage, JSON-compatible values, nested placeholders, graph binding, and SHA-256-shaped source snapshot hashes. The native trial runner now applies this schema only after trusted-envelope verification and records a canonical payload hash. Tests cover completeness, nested placeholders, missing fields, invalid snapshot hashes, unresolved records, and explicitly reviewed empty collections.

This is an initial structural contract, not yet the full field-specific semantic schema: the nested objects still need domain-specific types and cross-field referential-integrity checks. `TaskFlowSemanticProjection` still verifies only that a model preserves the submitted mapping in extensions; it does not prove the mapping is projected into typed architecture or consumed by a backend. The generic synthesizer and artifact-family derivation are not a substitute for this projection.

The native trial remains blocked until all of the following are complete:

1. A trusted reviewer resolves every field whose value is not derivable from the canonical snapshots.
2. The trusted envelope verifies against the exact ledger, graph, and snapshot hashes using an externally provisioned key.
3. Strict typed payload schemas and the deterministic projector are implemented and mutation-tested.
4. The live TaskFlow orchestration passes the same validated context through pre-synthesis and backend-planning boundaries.
5. Selected backends declare and satisfy the required semantic-consumption contract.
6. Two distinct end-to-end compilers run isolated generations from the same frozen input and acceptance suite.
7. Independent API, frontend, tenancy/RBAC, session, persistence, idempotency, negative-case, runtime, and traceability evaluation completes.

Until then, status remains BLOCKED / NOT RUN / UNKNOWN, not PASS.

## 5. Non-goals

This contract does not choose unresolved product semantics, authorize a reviewer decision, create a signature/envelope, choose a backend, claim provider-free end-to-end generation, or certify any generated application.
