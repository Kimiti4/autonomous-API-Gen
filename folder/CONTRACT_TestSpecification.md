# CONTRACT_TestSpecification (R1-B D18)

**Contract:** `Contract Test Specification`
**Status:** R1-B Deliverable D18. Authoritative specification of contract tests **before migration**. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Authority:** R1-B D02–D17.

**Invariants this contract satisfies:** All 15 INV-B invariants; the contract test specification is the verification surface for the invariants.

---

## 1. Purpose

This document specifies the **contract tests** that verify the canonical contracts satisfy their invariants. The tests are defined **before migration**; they are the acceptance criteria for R1-C and R1-D. They are **contract tests**, not the full implementation migration.

## 2. Test naming convention

```
test_<contract>_<invariant>
```

Example: `test_isr_hash_deterministic` verifies that the ISR's content hash is deterministic (a property required by D03).

## 3. Test catalogue

### 3.1 D02 RequirementGraph tests

| Test name | Verifies |
|---|---|
| `test_requirement_graph_identity_stable` | The graph's content hash is stable across identical inputs. |
| `test_requirement_graph_immutability` | The graph is frozen; attempts to modify it raise. |
| `test_requirement_graph_revision_creates_new_identity` | A "modification" creates a new graph with a new identity; the previous is preserved. |
| `test_requirement_graph_cycle_rejected` | A cycle in the dependency graph raises `RequirementGraphCycle`. |
| `test_requirement_graph_dangling_reference_rejected` | An edge referencing a non-existent requirement raises `RequirementGraphDanglingReference`. |
| `test_requirement_graph_conflict_queryable` | `CONFLICTS_WITH` edges are queryable; the contract does not auto-resolve. |
| `test_requirement_graph_refinement_closure` | `REFINES` is a partial order; transitive closure is queryable but not stored. |
| `test_requirement_graph_ownership_required` | Top-level requirements without `OWNED_BY` raise a validation error. |
| `test_requirement_graph_no_new_edge_types` | Adding a new edge type without an ADR is rejected. |

### 3.2 D03 CanonicalISR tests

| Test name | Verifies |
|---|---|
| `test_isr_identity_stable` | The ISR's content hash is stable across identical inputs. |
| `test_isr_hash_deterministic` | The hash is computed deterministically from the canonical serialization. |
| `test_isr_immutability` | The ISR is frozen; attempts to modify it raise. |
| `test_isr_forbidden_term_rejected` | An ISR containing any of the 25 forbidden terms raises `ISRInvariantViolation`. |
| `test_isr_node_type_taxonomy_frozen` | A new NodeType not in the canonical taxonomy is rejected. |
| `test_isr_edge_type_taxonomy_frozen` | A new EdgeType not in the canonical taxonomy is rejected. |
| `test_isr_edge_type_compatibility` | An edge with an incompatible (source, target) type pair raises `ISRInvariantViolation`. |
| `test_isr_round_trip_preserves_semantics` | `decode(encode(ISR)) ≡ ISR` (semantic equivalence, not just object identity). |
| `test_isr_provenance_in_content_hash` | The Provenance content hash is part of the ISR's content hash. |
| `test_isr_distinct_from_architecture_model` | The ISR and the ArchitectureCandidate are distinct semantic surfaces (D03 vs D04). |
| `test_isr_distinct_from_compiler_ir` | The ISR and the CompilerIR are distinct semantic surfaces (D03 vs D07). |
| `test_isr_distinct_from_generated_artifact` | The ISR and the ArtifactSet are distinct semantic surfaces (D03 vs D09). |

### 3.3 D04 ArchitectureCandidate tests

| Test name | Verifies |
|---|---|
| `test_architecture_references_isr` | An ArchitectureCandidate references an ISR revision by content hash. |
| `test_architecture_invalid_isr_reference_rejected` | A candidate without a valid ISR revision reference is rejected. |
| `test_architecture_does_not_become_isr` | A candidate that defines system semantics independently of the referenced ISR is rejected. |
| `test_architecture_immutability` | A candidate is frozen; attempts to modify it raise. |
| `test_architecture_parent_lineage` | A candidate's parent ID(s) are recorded. |
| `test_architecture_content_hash_deterministic` | The candidate's content hash is deterministic. |

### 3.4 D05 EvolutionOperation tests

| Test name | Verifies |
|---|---|
| `test_evolution_preserves_lineage` | The operation records parent candidate IDs. |
| `test_evolution_operation_identity_stable` | The operation ID is stable for identical (operator, parameters, seed). |
| `test_evolution_operation_replay_deterministic` | The same operation with the same seed produces the same output. |
| `test_evolution_real_crossover` | Crossover with two distinct parents produces a child that combines material from both (per `evolution/core/operations.py:74-104`). |
| `test_evolution_pseudo_crossover_rejected` | Substrate B's pseudo-crossover (copies parent A) is rejected as the canonical crossover. |
| `test_evolution_failure_recorded` | A failed operation produces a record with `status=OPERATION_FAILED`. |
| `test_evolution_precondition_blocked` | A blocked operation produces a record with `status=OPERATION_BLOCKED`. |
| `test_evolution_no_backend_dependency` | The operation does not reference a backend or technology. |

### 3.5 D06 EvolutionRecord tests

| Test name | Verifies |
|---|---|
| `test_eir_transformations_non_empty_for_success` | A record with `status=OPERATION_OK` has a non-empty `transformations` list. |
| `test_eir_records_actual_transformations` | The transformations in the record correspond to the actual mutations performed. |
| `test_eir_lineage_complete` | The record's lineage includes parent IDs, child IDs, operator, parameters, seed. |
| `test_eir_failure_recorded_not_dropped` | A failed operation produces a record (not silently dropped). |
| `test_eir_references_operation` | The record references the operation that produced it. |
| `test_eir_references_isr` | The record references the source and target ISR by content hash. |

### 3.6 D07 CanonicalCompilerIR tests

| Test name | Verifies |
|---|---|
| `test_compiler_ir_references_architecture` | The CompilerIR references the source ArchitectureCandidate by content hash. |
| `test_compiler_ir_references_isr` | The CompilerIR references the source ISR by content hash. |
| `test_compiler_ir_content_hash_deterministic` | The CompilerIR's content hash is deterministic. |
| `test_compiler_ir_distinct_from_isr` | The CompilerIR is a distinct semantic surface from the ISR. |
| `test_compiler_ir_distinct_from_generated_artifact` | The CompilerIR is a distinct semantic surface from the ArtifactSet. |
| `test_compiler_ir_bir_not_modified` | BIR is a semantic donor; BIR is **not** modified to add content-hash. |
| `test_compiler_ir_lowering_metadata_recorded` | Lowering metadata (operator, timestamp, chain) is part of the IR. |
| `test_compiler_ir_backend_constraints_recorded` | The IR declares which backends can lower it. |

### 3.7 D08 CompilerBackend tests

| Test name | Verifies |
|---|---|
| `test_backend_cannot_mutate_isr` | A backend that attempts to modify the ISR is rejected at registration. |
| `test_backend_cannot_modify_requirement_graph` | A backend that attempts to modify the RequirementGraph is rejected at registration. |
| `test_backend_unsupported_capability_explicit` | A backend that returns `COMPILATION_OK` for an unsupported capability is rejected. |
| `test_backend_pure_emission` | A backend does not write to the filesystem inside `compile()`. |
| `test_backend_version_compatibility` | A backend declares its `supported_ir_version`; the compiler checks the version. |
| `test_backend_returns_artifact_set` | A backend produces an `ArtifactSet` (not arbitrary files). |
| `test_backend_registration_rejects_violations` | A backend that violates INV-B08 is rejected at registration. |
| `test_backend_no_category_specific_authority` | Per-category compilers do not become a new architectural authority (INV-B14). |

### 3.8 D09 ArtifactSet tests

| Test name | Verifies |
|---|---|
| `test_artifact_set_traceability` | The ArtifactSet's provenance includes the full lineage (Requirement → ... → ArtifactSet). |
| `test_artifact_set_hash_per_file` | Each file in the ArtifactSet has a content hash. |
| `test_artifact_set_manifest_hash` | The manifest hash is computed over (file paths + content hashes + metadata). |
| `test_artifact_set_distinguishes_kinds` | The ArtifactSet distinguishes `generated artifact` / `compiler workspace` / `temporary build output` / `runtime deployment artifact`. |
| `test_artifact_set_incomplete_rejected` | A manifest with missing files is rejected. |
| `test_artifact_set_hash_mismatch_rejected` | A manifest with a hash mismatch is rejected. |
| `test_artifact_set_broken_lineage_rejected` | An ArtifactSet with a broken lineage (provenance hash mismatch) is rejected. |
| `test_artifact_set_no_filesystem_write_in_compile` | Backends that write to the filesystem inside `compile()` are rejected. |

### 3.9 D10 VerificationResult tests

| Test name | Verifies |
|---|---|
| `test_verification_exception_is_indeterminate` | An internal verifier exception produces `INDETERMINATE`, not `PASS`. |
| `test_verification_pass_only_on_success` | `PASS` is reached only when all checks pass. |
| `test_verification_fail_on_check_failure` | `FAIL` is reached when any check fails. |
| `test_verification_indeterminate_on_missing_evidence` | `INDETERMINATE` is reached when evidence is missing. |
| `test_verification_not_run_when_blocked` | `NOT_RUN` is reached when the verifier cannot run. |
| `test_verification_blocked_on_prerequisite` | `BLOCKED` is reached when a prerequisite is not met. |
| `test_verification_unsupported_capability_indeterminate` | A backend's `UNSUPPORTED_CAPABILITY` maps to `INDETERMINATE` at the verification level (D14). |
| `test_verification_five_states_required` | The 5-state model is mandatory; new states are added by ADR only. |

### 3.10 D11 CertificationEvidence tests

| Test name | Verifies |
|---|---|
| `test_certification_requires_evidence` | A CertificationEvidence record cannot be created without a corresponding VerificationResult. |
| `test_certification_cannot_manufacture_evidence` | A certification status that contradicts the verification result is rejected. |
| `test_certification_pass_maps_to_certified` | A `VerificationResult.PASS` maps to `CertificationEvidence.CERTIFIED` (subject to campaign rules). |
| `test_certification_indeterminate_not_certified` | A `VerificationResult.INDETERMINATE` maps to `CertificationEvidence.INDETERMINATE`, not `CERTIFIED`. |
| `test_certification_historical_immutability` | The B3-v2 evidence chain is preserved unchanged; historical records are not modified. |
| `test_certification_hash_chain_integrity` | Tampering with one record invalidates the chain after it. |
| `test_certification_campaign_identity_preserved` | Each record carries its campaign ID and run ID. |

### 3.11 D12 RuntimeObservation tests

| Test name | Verifies |
|---|---|
| `test_runtime_observation_traces_to_artifact` | An observation includes the full reverse lineage (deployment → ... → RequirementGraph). |
| `test_runtime_observation_broken_lineage_rejected` | An observation with missing reverse lineage is rejected. |
| `test_runtime_observation_does_not_make_autonomous_api_canonical` | The contract does not make `autonomous-api/` canonical; C-17 is deferred. |
| `test_runtime_observation_content_hash_deterministic` | The observation's content hash is deterministic. |

### 3.12 D13 Cross-contract identity & provenance tests

| Test name | Verifies |
|---|---|
| `test_cross_contract_identity_chain` | The identity chain Requirement → Artifact → Verification → Certification is end-to-end. |
| `test_cross_contract_parent_reference_by_content_hash` | Every cross-contract reference is by content hash. |
| `test_cross_contract_lineage_reconstructable` | Given any contract, the full lineage can be reconstructed. |
| `test_cross_contract_broken_lineage_rejected` | A contract with a broken parent reference is rejected. |
| `test_cross_contract_hash_mismatch_rejected` | A contract with a content hash that does not match its serialization is rejected. |

### 3.13 D14 State machine & failure semantics tests

| Test name | Verifies |
|---|---|
| `test_state_machine_validation_failure_not_warning` | A validation failure is not converted to a warning. |
| `test_state_machine_verification_exception_not_success` | A verification exception is not converted to `PASS`. |
| `test_state_machine_unsupported_capability_not_success` | An unsupported backend capability is not converted to `COMPILATION_OK`. |
| `test_state_machine_missing_evidence_not_certified` | Missing evidence does not produce `CERTIFIED`. |
| `test_state_machine_cross_contract_mapping` | The cross-contract state mapping (D14) is enforced. |

### 3.14 D16 Invariants tests

| Test name | Verifies |
|---|---|
| `test_invariant_b01_one_canonical_isr` | INV-B01: one canonical ISR semantic authority. |
| `test_invariant_b02_requirement_graph_precedes_isr` | INV-B02. |
| `test_invariant_b03_isr_technology_neutral` | INV-B03. |
| `test_invariant_b04_architecture_distinct_from_isr` | INV-B04. |
| `test_invariant_b05_compiler_ir_distinct_from_isr` | INV-B05. |
| `test_invariant_b06_compiler_ir_distinct_from_artifact` | INV-B06. |
| `test_invariant_b07_evolution_no_backend_dependency` | INV-B07. |
| `test_invariant_b08_backend_cannot_redefine_upstream` | INV-B08. |
| `test_invariant_b09_artifact_set_is_boundary` | INV-B09. |
| `test_invariant_b10_verification_cannot_fail_open` | INV-B10. |
| `test_invariant_b11_certification_cannot_manufacture_evidence` | INV-B11. |
| `test_invariant_b12_runtime_observations_retain_lineage` | INV-B12. |
| `test_invariant_b13_historical_evidence_immutable` | INV-B13. |
| `test_invariant_b14_no_category_specific_authority` | INV-B14. |
| `test_invariant_b15_legacy_adapters_one_way` | INV-B15. |

### 3.15 D17 Legacy boundary tests

| Test name | Verifies |
|---|---|
| `test_legacy_classification_present` | Each legacy component has a `LEGACY` classification. |
| `test_legacy_owner_present` | Each legacy component has an owner (the migration step that retires it). |
| `test_legacy_canonical_destination_present` | Each legacy component has a canonical destination. |
| `test_legacy_retirement_condition_present` | Each legacy component has a retirement condition. |
| `test_legacy_adapter_one_way` | Legacy adapters are one-way: `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY` (INV-B15). |
| `test_legacy_bidirectional_adapter_rejected` | A bidirectional adapter is rejected. |

## 4. Test execution

The contract tests are executed in the canonical runtime's test suite. They are the **first acceptance criterion** for R1-C and R1-D: a migration step is accepted only if the corresponding contract tests pass.

The 243 Tier A CBC1 tests are not the contract tests; they are the certification tier. The contract tests (D18) are the **architectural acceptance** tier. They run against the canonical implementation, not against the campaign runtime.

## 5. Test tiering

| Tier | Purpose | Authority |
|---|---|---|
| Contract tests (D18) | Architectural acceptance | R1-B |
| Tier A CBC1 (243 tests) | Certification tier | Phase 31 |
| Tier C (`pytest -m certification`, 40 tests) | Authoritative certification | Phase 31 |

The contract tests are a **new tier** introduced by R1-B. They are not a replacement for the existing tiers; they are orthogonal.

## 6. Field classification

| Field | Classification |
|---|---|
| Test name, test purpose | **semantic** (defines the contract's correctness) |
| Test execution context | **observational metadata** |

## 7. Cross-references

- D02–D17: per-contract specifications.
- D20: R1-B gate report (the gate evaluates the contract test coverage).

---

*End of D18. The contract test specification enumerates the tests that verify the canonical contracts satisfy their invariants. The tests are the architectural acceptance tier; they are defined before migration and are the first acceptance criterion for R1-C and R1-D.*
