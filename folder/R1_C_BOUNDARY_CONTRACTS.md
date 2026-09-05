# R1_C_BOUNDARY_CONTRACTS (R1-C C02)

**Status:** R1-C Deliverable C02. Formal adapter boundary definitions for the non-DEFER crossings in C01. Index: `folder/R1_C_ADAPTER_INVENTORY.md` (C01), `folder/R1_B_CONTRACT_GATE_REPORT.md` (D20), `folder/CONTRACT_LegacyBoundarySpecification.md` (D17).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; the R1-C master prompt.

**Critical rule (per R1-A + D17 + INV-B15):** Adapters are always `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY`. The canonical runtime remains authoritative.

**Important:** C02 is a **contract definition** (documentation). C03–C12 are the next gate; they implement these contracts. No code modifications in R1-C C02.

---

## 0. Adapter ID scheme

Each adapter is named:

```text
ADAPTER-<DOMAIN>-<NUMBER>
```

Where:
- `<DOMAIN>` is the contract area (e.g. `VALID`, `NORM`, `VERIFY`, `ARTIFACT`, `ISR-VALID`, `BIR`, `EIR`, `CAP`, `LINEAGE`, `EVOL-OP`).
- `<NUMBER>` is a sequence number for that domain.

Each adapter has a direction:

```text
LEGACY → CANONICAL
```

**No `CANONICAL → LEGACY` adapters are defined in R1-C.** (Per the R1-C spec §2, a `CANONICAL → LEGACY` adapter is permitted only when producing a non-authoritative compatibility/output representation and only where explicitly documented. None of the C02 adapters fall in this category; all are LEGACY → CANONICAL.)

---

## 1. ADAPTER-VALID-001 — Constitutional validation pass → canonical Validation contract

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-VALID-001` |
| **Source contract** | `constitutional_architecture/compiler/passes/validation_pass.py:7-31` (Gen-C validation pass) |
| **Destination contract** | The canonical Validation pass contract (D14) — `PassResult(success=..., state=...)` with `state ∈ {PASS, FAIL, BLOCKED, INDETERMINATE, SKIPPED}`. Fail-closed. |
| **Input** | A compiler context (the Gen-C pipeline's context) |
| **Output** | A canonical `PassResult` |
| **Semantic transformation** | The constitutional validation pass's `try: ... except Exception as e: ctx.diagnostics.info("COMP-VAL-003", ...); return PassResult(success=True, ...)` (fail-open) is replaced with: `return PassResult(success=result.passed, state=...)` where `state` is determined by `result.passed` and the failure-semantics discipline. The type checker's `result.passed` is honored (not silently coerced to `success=True`). |
| **Identity transformation** | The canonical `PassResult` has a canonical identity (per D14). The pass instance is identified by its name + version. |
| **Provenance transformation** | The pass records the source pass identity, the canonical contract version, and the transformation timestamp. |
| **Failure behavior** | `INDETERMINATE` on internal exception; `FAIL` on type-check failure; `BLOCKED` on prerequisite not met; `PASS` only on success. **Never** `success=True` on failure. |
| **Version compatibility** | Adapts Gen-C validation pass v1 to canonical Validation contract v1.0.0. |
| **Retirement condition** | The Gen-C validation pass is replaced by the canonical Validation contract's implementation; the legacy pass is removed. |
| **Tests** | (a) `test_validation_pass_fail_closed_on_exception` — internal exception produces `INDETERMINATE`, not `PASS`. (b) `test_validation_pass_honors_type_checker` — `result.passed=False` produces `FAIL`, not `PASS`. (c) `test_validation_pass_blocked_on_prerequisite` — prerequisite not met produces `BLOCKED`. (d) `test_validation_pass_idempotent` — repeated runs produce the same `PassResult` for the same input. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-E.2 (canonical Validation pass contract implementation; adapt the Gen-C pass) |
| **Classification** | ADAPT (per C01 §1.20) |

---

## 2. ADAPTER-NORM-001 — Constitutional normalization pass → canonical Normalization contract

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-NORM-001` |
| **Source contract** | `constitutional_architecture/compiler/passes/normalization_pass.py:19-156` (Gen-C normalization pass; carries only 7 of 21 System fields) |
| **Destination contract** | The canonical Normalization contract (D14) — preserves all System fields; rebuilds via `with_system`. |
| **Input** | A rich `ISR` (from `constitutional_architecture.isr.model.isr.ISR`) |
| **Output** | A normalized canonical ISR (preserving all System fields) |
| **Semantic transformation** | The constitutional normalization reconstructs `System` with only `id, name, description, modules, deployment, metadata, global_policies`. The canonical normalization must carry all 21 System fields: `business_capabilities, requirements, acceptance_criteria, deployment_intents, testing_anchors, documentation_intents, evolution_objectives, protected_regions, evolution_policies, architectural_decisions, security_threats, reliability_requirements, architectural_boundaries, constraints, modules, deployment, metadata, global_policies`. |
| **Identity transformation** | The normalized canonical ISR has a content-hash identity (per D03). The constitutional normalization's identity is the constitutional `System` ID; the canonical identity is the content hash. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | Fail-closed. A normalization that would discard fields raises `CanonicalNormalizationSemanticLoss`. |
| **Version compatibility** | Adapts Gen-C normalization pass v1 to canonical Normalization contract v1.0.0. |
| **Retirement condition** | The Gen-C normalization pass is replaced by the canonical Normalization contract's implementation; the legacy pass is removed. |
| **Tests** | (a) `test_normalization_preserves_all_system_fields` — all 21 System fields are carried forward. (b) `test_normalization_preserves_module_constraints` — `module.constraints` is preserved (the audit's defect). (c) `test_normalization_with_system_rebuild` — the canonical normalization uses `with_system` to create a new immutable ISR. (d) `test_normalization_idempotent` — repeated normalization produces the same canonical ISR. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-E.4 (canonical Normalization contract implementation; adapt the Gen-C pass) |
| **Classification** | ADAPT (per C01 §1.21) |

---

## 3. ADAPTER-VERIFY-001 — Constitutional verification pass → canonical Verification contract

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-VERIFY-001` |
| **Source contract** | `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (Gen-C verification pass; fail-open: returns `success=True` on engine exception) |
| **Destination contract** | The canonical Verification contract (D10, D14) — `VerificationResult` with `result ∈ {PASS, FAIL, INDETERMINATE, NOT_RUN, BLOCKED}`. Fail-closed. |
| **Input** | A compiler context (the Gen-C pipeline's context) |
| **Output** | A canonical `VerificationResult` |
| **Semantic transformation** | The constitutional verification pass's `try: ... except Exception as e: ctx.diagnostics.warning("COMP-VERIFY-001", ...); return success=not ctx.diagnostics.has_errors` (fail-open) is replaced with: an internal exception produces `VerificationResult(result=INDETERMINATE, indeterminate_reason=str(e))`. The 5-state model is mandatory. The cross-contract state mapping (D14) is enforced. |
| **Identity transformation** | Canonical. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | `INDETERMINATE` on engine exception; `FAIL` on check failure; `PASS` only on success. **Never** `PASS` on engine exception. |
| **Version compatibility** | Adapts Gen-C verification pass v1 to canonical Verification contract v1.0.0. |
| **Retirement condition** | The Gen-C verification pass is replaced by the canonical Verification contract's implementation; the legacy pass is removed. |
| **Tests** | (a) `test_verification_engine_exception_is_indeterminate` — internal exception produces `INDETERMINATE`, not `PASS`. (b) `test_verification_pass_only_on_success` — `PASS` only on success. (c) `test_verification_indeterminate_on_missing_evidence` — missing evidence produces `INDETERMINATE`. (d) `test_verification_blocked_on_prerequisite` — prerequisite not met produces `BLOCKED`. (e) `test_verification_unsupported_capability_indeterminate` — backend `UNSUPPORTED_CAPABILITY` maps to `INDETERMINATE` (per D14). |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-E.1 (canonical Verification contract implementation; adapt the Gen-C pass) |
| **Classification** | ADAPT (per C01 §1.26) |

---

## 4. ADAPTER-ARTIFACT-001 — Gen-C fastapi_backend → canonical CompilerBackend (artifact purity)

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-ARTIFACT-001` |
| **Source contract** | `constitutional_architecture/compiler/backends/fastapi_backend.py:47-719` (Gen-C FastAPI backend with `self.write_files()` defect at line 85) |
| **Destination contract** | The canonical CompilerBackend protocol (D08) — `CompilerIR → CompilerBackend → ArtifactSet`. **No filesystem emission inside `compile()`.** |
| **Input** | A `BIR` (or, in the migration window, a canonical CompilerIR) |
| **Output** | An `ArtifactSet` (D09) — pure emission |
| **Semantic transformation** | The constitutional `compile(bir, bindings)` calls `self.write_files()` (line 85) which writes directly to the filesystem. The canonical contract requires the backend to return an `ArtifactSet`; the packager writes. The semantic content of the generated files is preserved; the **boundary** is moved from inside-`compile` to outside-`compile`. |
| **Identity transformation** | The `ArtifactSet` has a manifest hash (per D09). The backend's identity is `fastapi@<version>`. |
| **Provenance transformation** | The `ArtifactSet` carries the full lineage (Requirement → ... → ArtifactSet; per D09). |
| **Failure behavior** | `UNSUPPORTED_CAPABILITY` for capabilities the backend cannot lower; the cross-contract state mapping (D14) routes this to `Verification INDETERMINATE` (per the R1-B gate decision A). |
| **Version compatibility** | Adapts Gen-C fastapi_backend v1 to canonical CompilerBackend v1.0.0. |
| **Retirement condition** | The Gen-C fastapi_backend is replaced by a canonical backend that returns an `ArtifactSet`; the legacy backend is removed. |
| **Tests** | (a) `test_fastapi_backend_returns_artifact_set` — the backend returns an `ArtifactSet`, not filesystem writes. (b) `test_fastapi_backend_no_filesystem_write_in_compile` — `compile()` does not call `self.write_files()`. (c) `test_fastapi_backend_unsupported_capability` — `UNSUPPORTED_CAPABILITY` is returned, not a successful compilation. (d) `test_fastapi_backend_artifact_set_traceability` — the `ArtifactSet` carries the full lineage. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-E.7 (canonical CompilerBackend implementation; adapt the Gen-C fastapi_backend) |
| **Classification** | ADAPT (per C01 §1.28) |

---

## 5. ADAPTER-ISR-VALID-001 — Constitutional ISR semantic validators → `isr/core/invariants.py`

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-ISR-VALID-001` |
| **Source contract** | `constitutional_architecture/isr/semantics/*` (semantic validators; e.g. `requirement.py`, `boundary.py`) |
| **Destination contract** | `isr/core/invariants.py` (the canonical ISR invariant validators) — `validate_invariants` at `isr/core/invariants.py:50-109` |
| **Input** | A canonical ISR (or a constitutional ISR validator function) |
| **Output** | A canonical invariant validation result |
| **Semantic transformation** | Genuinely-semantic validator functions (e.g. requirement-layer semantic obligation / test / verification distinction, technology-leakage rejection) are absorbed into `isr/core/invariants.py`. The constitutional model type (e.g. `Requirement`) is **not** migrated. The semantic property is what migrates. |
| **Identity transformation** | Canonical. The new invariant function has a canonical identity (module + name). |
| **Provenance transformation** | The source of the absorbed validator is recorded in the docstring. |
| **Failure behavior** | Fail-closed. The absorbed invariants follow the canonical invariant discipline (raise `ISRInvariantViolation` on violation). |
| **Version compatibility** | Adapts constitutional semantics v1 to canonical invariants v1.0.0. |
| **Retirement condition** | All genuinely-semantic validators are absorbed; the constitutional semantics module has no canonical consumer. |
| **Tests** | (a) `test_isr_invariant_absorbed_semantics` — each absorbed semantic validator raises `ISRInvariantViolation` on violation. (b) `test_isr_invariant_fail_closed` — exceptions are not silently coerced. (c) `test_isr_invariant_technology_neutral` — absorbed validators do not introduce forbidden terms. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-D.1 (semantic migration into `isr/core/`) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.1, §1.2) |

---

## 6. ADAPTER-BIR-001 — BIRNodeTypes → canonical CompilerIR (semantic donor)

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-BIR-001` |
| **Source contract** | `constitutional_architecture/compiler/bir/model.py:BIR` (9 BIRNodeType: HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST) |
| **Destination contract** | The canonical CompilerIR contract (D07) — to be created in R1-D.2 |
| **Input** | BIRNodeType concepts (read as references, not as live BIR instances) |
| **Output** | Canonical CompilerIR node type concepts (selectively absorbed) |
| **Semantic transformation** | Each BIRNodeType is evaluated for genuinely-semantic content. The ones that are genuinely semantic (e.g. HANDLER, ENTITY, SERVICE) are absorbed as canonical CompilerIR node types. The ones that are not (e.g. CONFIG) are deferred. **BIR is NOT modified to add content-hash; content-hash is added to the canonical CompilerIR, not to BIR.** |
| **Identity transformation** | Canonical. The absorbed concepts have canonical names and content-hash identities. |
| **Provenance transformation** | The source BIRNodeType is recorded in the canonical node type's docstring. |
| **Failure behavior** | A BIRNodeType that is not genuinely semantic is not absorbed; the migration is selective. |
| **Version compatibility** | Reads BIR v1 as references; absorbs into canonical CompilerIR v1.0.0. |
| **Retirement condition** | All genuinely-semantic BIRNodeType concepts are absorbed; BIR is retired as runtime. |
| **Tests** | (a) `test_bir_nodetype_selective_absorption` — only genuinely-semantic BIRNodeTypes are absorbed. (b) `test_bir_not_modified` — BIR is read as references, not modified. (c) `test_canonical_compiler_ir_has_content_hash` — the canonical CompilerIR has content-hash; BIR does not (and is not modified to add it). |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-D.2 (canonical CompilerIR creation) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.19; BIR is a semantic donor) |

---

## 7. ADAPTER-EIR-001 — Constitutional EIR schema fragments → canonical EvolutionRecord

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-EIR-001` |
| **Source contract** | `constitutional_architecture/eir/transformation.py:Transformation` (lines 46-54) |
| **Destination contract** | The canonical EvolutionRecord (D06) — to be created in R1-D.3 as `evolution/core/record.py` |
| **Input** | A `Transformation` instance (constitutional EIR) |
| **Output** | Canonical EvolutionRecord fields |
| **Semantic transformation** | The audit-required fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`) are added to the canonical EvolutionRecord. The constitutional EIR's `Transformation.type`, `Transformation.target`, `Transformation.parameters`, `Transformation.fitness_impact`, `Transformation.reversible`, `Transformation.description` are selectively absorbed where genuinely semantic. |
| **Identity transformation** | Canonical. The canonical EvolutionRecord has a content-hash identity (per D06). The constitutional `Transformation` ID is replaced by the canonical `transformation_id`. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | A constitutional EIR record that would map to an empty `transformations` list (the `evolution_loop.py:110` defect) is rejected. The `transformations=[]` defect is repaired or the path is retired. |
| **Version compatibility** | Adapts constitutional EIR v1 to canonical EvolutionRecord v1.0.0. |
| **Retirement condition** | All audit-required fields are added; useful schema fragments are absorbed; the `transformations=[]` defect is repaired or the path is retired. |
| **Tests** | (a) `test_eir_canonical_record_has_audit_required_fields` — the canonical EvolutionRecord has all audit-required fields. (b) `test_eir_transformations_non_empty_for_success` — a record with `status=OPERATION_OK` has a non-empty `transformations` list. (c) `test_eir_failure_recorded_not_dropped` — a failed operation produces a record, not a silent drop. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-D.3 (canonical EvolutionRecord creation) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.11) |

---

## 8. ADAPTER-CAP-001 — Constitutional capabilities → canonical capability resolution

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-CAP-001` |
| **Source contract** | `constitutional_architecture/compiler/passes/capability_resolution_pass.py:8-78` (13+ capabilities: OAUTH2, JWT_AUTH, REST_API, INPUT_VALIDATION, SERIALIZATION, ORM, MIGRATIONS, VALIDATION, STRUCTURED_LOGGING, HEALTH_CHECKS, CONTAINERIZATION, METRICS, DISTRIBUTED_TRACING) |
| **Destination contract** | The canonical CompilerIR's capability resolution (per D08) — abstract capabilities: authentication, authorization, persistence, REST, eventing, logging, metrics, tracing, validation, containerization, migration. |
| **Input** | A constitutional capability (e.g. `OAUTH2`) |
| **Output** | A canonical capability (e.g. `authentication`) |
| **Semantic transformation** | Each constitutional capability is evaluated for genuinely-semantic content. The ones that map to canonical capabilities (e.g. `OAUTH2` → `authentication`) are absorbed. The ones that are technology-specific (e.g. `OAUTH2` if mapped to a specific OAuth provider) are **not** absorbed; technology specificity belongs in the backend, not the canonical IR. |
| **Identity transformation** | Canonical. The absorbed capability has a canonical name. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | A capability that is technology-specific is not absorbed. The mapping is technology-neutral. |
| **Version compatibility** | Reads constitutional capabilities v1 as references; absorbs into canonical capabilities v1.0.0. |
| **Retirement condition** | All genuinely-semantic capabilities are absorbed; the constitutional capability set is reduced to the canonical capability set. |
| **Tests** | (a) `test_capability_abstract_absorption` — abstract capabilities (authentication, authorization, etc.) are absorbed. (b) `test_capability_technology_specific_rejected` — technology-specific capabilities (e.g. `OAUTH2` if mapped to a specific provider) are not absorbed. (c) `test_capability_ir_has_capability_constraints` — the canonical CompilerIR has `backend_constraints` (per D07). |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-D.2 (canonical CompilerIR creation) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.23) |

---

## 9. ADAPTER-LINEAGE-001 — Constitutional lineage → canonical lineage (durable)

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-LINEAGE-001` |
| **Source contract** | `constitutional_architecture/isr/versioning/LineageTracker` and `constitutional_architecture/engine/lineage_tracker.py` (in-memory) |
| **Destination contract** | The canonical lineage — `evolution/core/lineage` (in-memory) + `release/evidence/` (durable hash-chained; per D11 + R1-E.6) |
| **Input** | A constitutional lineage record |
| **Output** | A canonical lineage record (durable, hash-chained) |
| **Semantic transformation** | The semantic concept of lineage is captured. The canonical lineage is **durable** (the constitutional `LineageTracker` is in-memory and is insufficient per the audit). |
| **Identity transformation** | The canonical lineage has a content-hash identity. The constitutional lineage ID is replaced by the canonical content hash. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | Fail-closed. |
| **Version compatibility** | Adapts constitutional lineage v1 to canonical lineage v1.0.0. |
| **Retirement condition** | The constitutional `LineageTracker` is replaced by the canonical durable lineage. |
| **Tests** | (a) `test_lineage_durable` — the canonical lineage is persisted to `release/evidence/`. (b) `test_lineage_hash_chained` — the canonical lineage is hash-chained. (c) `test_lineage_reconstructable` — given any lineage record, the full lineage can be reconstructed. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-E.6 (durable lineage) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.3, §1.16) |

---

## 10. ADAPTER-EVOL-OP-001 — Constitutional mutation operators → canonical Evolution operators

| Field | Value |
|---|---|
| **Adapter ID** | `ADAPTER-EVOL-OP-001` |
| **Source contract** | `constitutional_architecture/engine/mutation_*.py` (6 mutation operator files) |
| **Destination contract** | The canonical Evolution operators (`evolution/core/operations.py`) |
| **Input** | A constitutional mutation operator |
| **Output** | A canonical Evolution operator (per D05) |
| **Semantic transformation** | Each constitutional mutation operator is evaluated for genuinely-new operator kinds. The ones that add genuinely-new operator kinds are absorbed into `evolution/core/operations.py`. The ones that duplicate existing canonical operators are not absorbed. |
| **Identity transformation** | Canonical. |
| **Provenance transformation** | Recorded. |
| **Failure behavior** | A constitutional operator that does not add a new operator kind is not absorbed. |
| **Version compatibility** | Reads constitutional operators v1 as references; absorbs into canonical operators v1.0.0. |
| **Retirement condition** | All genuinely-new operator kinds are absorbed; the constitutional mutation operators have no canonical consumer. |
| **Tests** | (a) `test_mutation_operator_selective_absorption` — only genuinely-new operator kinds are absorbed. (b) `test_mutation_operator_no_backend_dependency` — absorbed operators do not reference a backend or technology. (c) `test_mutation_operator_real_crossover_preserved` — the real crossover in `evolution/core/operations.py:74-104` is preserved. |
| **Direction** | `LEGACY → CANONICAL` |
| **Migration step** | R1-D.3 (canonical Evolution operators) |
| **Classification** | MIGRATE_SEMANTICS (per C01 §1.12) |

---

## 11. RETIRE-CBRIDGE-001 — Dead code retirement: `compiler_bridge.py`

| Field | Value |
|---|---|
| **Adapter ID** | `RETIRE-CBRIDGE-001` |
| **Source contract** | `constitutional_architecture/engine/compiler_bridge.py:13-45` |
| **Destination contract** | None (DEAD CODE) |
| **Input** | n/a |
| **Output** | n/a |
| **Semantic transformation** | n/a |
| **Identity transformation** | n/a |
| **Provenance transformation** | n/a |
| **Failure behavior** | n/a |
| **Version compatibility** | n/a |
| **Retirement condition** | **Immediate.** The bridge is dead code with no callers; `grep -r "constitutional_architecture.engine.compiler_bridge" .` returns only the bridge itself. The file is removed in R1-D.5. |
| **Tests** | (a) `test_compiler_bridge_no_callers` — `grep` confirms no callers. (b) `test_compiler_bridge_removed` — the file is removed; the build still passes. |
| **Direction** | n/a (RETIRE, not ADAPT) |
| **Migration step** | R1-D.5 (immediate removal) |
| **Classification** | RETIRE (per C01 §1.15; D17 L13) |

---

## 12. RETIRE items (per D17 L01–L14)

The following legacy items are retired per D17 L01–L14. Each has a clear canonical destination (or is retired entirely). No adapter is required; the items are removed in R1-D.5.

| L# | Legacy item | Canonical destination | Classification | Migration step |
|---|---|---|---|---|
| L01 | `constitutional_architecture/isr/model/isr.py:ISR` | None (semantic validators → `isr/core/invariants.py` per ADAPTER-ISR-VALID-001) | MIGRATE_SEMANTICS (validators) + RETIRE (model) | R1-D.1, R1-D.5 |
| L02 | `constitutional_architecture/core/models/isr.py:UniversalISR` | None (no canonical consumer) | RETIRE | R1-D.5 |
| L03 | `constitutional_architecture/engine/evolution_engine.py` + `individual.py` | `evolution/core/` (selective operator absorption per ADAPTER-EVOL-OP-001) | MIGRATE_SEMANTICS | R1-D.3 |
| L04 | `constitutional_architecture/engine/mutation_*.py` (6 files) | `evolution/core/operations.py` (per ADAPTER-EVOL-OP-001) | MIGRATE_SEMANTICS | R1-D.3 |
| L05 | `constitutional_architecture/engine/crossover_engine.py` | None (pseudo-crossover; canonical crossover is the real one) | RETIRE | R1-D.5 |
| L06 | `constitutional_architecture/eir/transformation.py:EIR` | `evolution/core/record.py` (per ADAPTER-EIR-001) | MIGRATE_SEMANTICS | R1-D.3 |
| L07 | `constitutional_architecture/compiler/bir/model.py:BIR` | Canonical CompilerIR (per ADAPTER-BIR-001) | MIGRATE_SEMANTICS (semantic donor) | R1-D.2 |
| L08 | `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` | None (canonical protocol is `compiler/core/protocol.py`) | RETIRE | R1-D.5 |
| L09 | `compiler/sdk/base.py:CompilerBackendBase` (Gen-A) | None (canonical protocol is Gen-B) | RETIRE | R1-D.5 |
| L10 | `constitutional_architecture/compilers/*` (9 per-category) | None (INV-B14) | RETIRE | R1-D.5 |
| L11 | `constitutional_architecture/compiler/backends/fastapi_backend.py` | Canonical CompilerBackend (per ADAPTER-ARTIFACT-001) | ADAPT (artifact purity) | R1-E.7 |
| L12 | `constitutional_architecture/compiler/passes/verification_pass.py` | Canonical Verification (per ADAPTER-VERIFY-001) | ADAPT (fail-closed) | R1-E.1 |
| L13 | `constitutional_architecture/engine/compiler_bridge.py` | None (DEAD CODE) | RETIRE (immediate) | R1-D.5 |
| L14 | `autonomous-api/*` | None (C-17 DEFER) | DEFER | R2/R3 |

---

## 13. KEEP items (canonical runtime, no migration required)

The following are kept as-is (the canonical runtime). No adapter is required.

- **C01 RequirementGraph** (`reqgraph/core/`) — KEEP.
- **C02 ISR** (`isr/core/`) — KEEP. (ADAPTER-ISR-VALID-001 is the legacy→canonical direction for semantic validators; the canonical ISR itself is unchanged.)
- **C10 CertificationEvidence** (`certification/evidence/`) — KEEP. Frozen.
- **`certification/`** — KEEP. Frozen during R1-C.
- **`release/evidence/`** — KEEP. Frozen during R1-C.
- **`constitutional_architecture/governance/*`** — KEEP (as governance/specification, not runtime).
- **`constitutional_architecture/core/contracts/*`** — KEEP (the canonical contracts are the R1-B deliverables).
- **`constitutional_architecture/schemas/*`** — KEEP (the canonical schemas are the R1-B deliverables).

---

## 14. DEFER items (out of R1 scope)

- **C11 RuntimeObservation** (D12) — contract defined; implementation deferred to R2/R3 (C-17).
- **`autonomous-api/*`** — C-17 DEFER to R2/R3.
- **`knowledge/*`**, **`civilization/*`**, **`autonomous_network/*`**, **`distributed_evolution/*`** — out of R1 scope.
- **`generated/testshop/`**, **`generated/monolithshop/`** — LEGACY_GENERATED; out of R1 scope.
- **C-18 (`pyproject.toml` topology)** — post-R1 packaging cleanup.
- **Constitutional `views/*`, `profiles/*`, `agents/*`, `ckb/*`, `deployment/*`, `frontend/*`, `generated/*`, `meta/*`** — out of R1 scope.

---

## 15. Adapter-test strategy

The adapter contract tests (R1-C C08) verify:

1. **Determinism:** same valid source → same canonical result.
2. **Identity:** canonical result has stable identity.
3. **Provenance:** source identity remains traceable.
4. **Semantic preservation:** required fields survive transformation.
5. **Failure behavior:** invalid source does not become valid through silent coercion.
6. **One-way boundary:** canonical state cannot silently mutate legacy state.
7. **Unsupported semantics:** unsupported information is explicitly surfaced.
8. **Idempotence where applicable:** repeated adaptation of an already canonical representation must not create semantic drift.

The tests are defined for each adapter in §1–§10 above. C08 is the next gate; it implements the test suite.

---

## 16. Cross-references

- C01: adapter inventory (the source of this contract).
- D17: legacy boundary specification (L01–L14, cross-referenced in §12).
- D20: R1-B gate report (R1-B PASS).
- R1-A: canonical substrate decision.

---

*End of C02. The 11 boundary contracts are defined: 4 ADAPT, 6 MIGRATE_SEMANTICS, 1 RETIRE (immediate), and 14 RETIRE cross-referenced from D17. C03–C12 are the next gate; they implement these contracts. C02 does NOT authorize code modifications.*
