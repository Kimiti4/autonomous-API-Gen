# R1_D2_COMPILER_IR_SEMANTIC_COMPARISON (R1-D.2 D2-D3)

**Status:** R1-D.2 Deliverable D2-D3. Compiler IR semantic comparison. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md` (D2-D2), `folder/CONTRACT_CanonicalCompilerIR.md` (D07 R1-B).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

**Method:** Field-by-field and concept-by-concept comparison. Each row is OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN.

---

## 1. Purpose

Compare the Compiler IR candidates:
- `CompilationPlan` (`compiler/core/plan.py:32-40`) — the canonical stabilization.
- `BIR` (`constitutional_architecture/compiler/bir/model.py:36-40`) — the constitutional semantic donor.
- Gen-C IR/passes (`constitutional_architecture/compiler/`) — the constitutional pipeline.
- Other IRs (per-category compilers' `CompilationBundle`).

Against the R1-B Compiler IR contract (`folder/CONTRACT_CanonicalCompilerIR.md`, D07).

Classify each semantic: CANONICALIZE / MIGRATE / SPLIT / REPLACE / REJECT / DEFER.

---

## 2. Node type comparison

| Node concept | `CompilationPlan` (canonical stabilization) | `BIR` (semantic donor) | Gen-C IR | R1-B D07 contract | Action | Reason |
|---|---|---|---|---|---|---|
| Service | ✓ (`Service` at `compiler/core/plan.py:23-30`) | ✓ (`BIRNodeType.SERVICE`) | (implied by lowering) | ✓ (canonical) | **RETAIN CANONICAL** | The canonical `Service` has id, name, data_models, published_events, consumed_events. BIR's `SERVICE` is similar. |
| Data model | ✓ (`DataModel` at `compiler/core/plan.py:6-10`) | ✓ (`BIRNodeType.ENTITY`) | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | |
| Event | ✓ (`Event` at `compiler/core/plan.py:12-15`) | ✗ (BIR has `EVENT_HANDLER`, not `EVENT`) | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | The canonical `Event` is distinct from BIR's `EVENT_HANDLER`. The canonical semantics: an event is a domain occurrence; the handler is the implementation. |
| Security policy | ✓ (`SecurityPolicy` at `compiler/core/plan.py:18-20`) | ✗ | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | |
| Handler | ✗ | ✓ (`BIRNodeType.HANDLER`) | (implied) | ✗ (not in flat 9-node) | **DEFER** | Handlers are implementation concerns, not canonical IR semantics. |
| Repository | ✗ | ✓ (`BIRNodeType.REPOSITORY`) | (implied) | ✗ | **DEFER** | Repositories are persistence patterns; the canonical IR expresses "persistence requirement" abstractly. |
| Router | ✗ | ✓ (`BIRNodeType.ROUTER`) | (implied) | ✗ | **DEFER** | Routers are backend-specific. |
| Config | ✗ | ✓ (`BIRNodeType.CONFIG`) | (implied) | ✗ | **DEFER** | Configuration is backend-specific. |
| Middleware | ✗ | ✓ (`BIRNodeType.MIDDLEWARE`) | (implied) | ✗ | **DEFER** | Middleware is backend-specific. |
| Event handler | ✗ | ✓ (`BIRNodeType.EVENT_HANDLER`) | (implied) | ✗ | **DEFER** | Event handlers are implementation patterns. |
| Test | ✗ | ✓ (`BIRNodeType.TEST`) | (implied) | ✗ | **DEFER** | Tests are generated; the IR doesn't need a test node type. |
| Module | ✗ | ✓ (`BIRModule`) | (implied) | ✗ | **REJECT** | The canonical IR is flat; module is a grouping. |
| Project | ✓ (`isr_id` field on `CompilationPlan`) | ✓ (`BIR.project_name`) | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | |

**Summary:** 4 canonical node types retained (`Service`, `DataModel`, `Event`, `SecurityPolicy`); 7 BIR types deferred; 1 type rejected (module); 1 type (project) retained.

---

## 3. Edge/relationship comparison

| Edge concept | `CompilationPlan` | `BIR` | Gen-C | R1-B D07 | Action | Reason |
|---|---|---|---|---|---|---|
| Service persists DataModel | ✓ (`Service.data_models: list[DataModel]`) | ✓ (via `children: tuple[BIRNode, ...]`) | (implied by lowering) | ✓ (canonical) | **RETAIN CANONICAL** | The canonical representation is a nested list of DataModel references. |
| Service publishes Event | ✓ (`Service.published_events: list[Event]`) | ✓ (via children) | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | |
| Service consumes Event | ✓ (`Service.consumed_events: list[Event]`) | ✓ (via children) | (implied) | ✓ (canonical) | **RETAIN CANONICAL** | |
| Service secured by SecurityPolicy | ✗ (not in CompilationPlan) | ✗ | (implied) | ✓ (canonical) | **MIGRATE** | Add `Service.security: list[SecurityPolicy]` to `CompilationPlan`. This is a genuine semantic the canonical IR should carry. |
| Service depends on Service | ✗ | ✗ | (implied) | ✗ | **DEFER** | Dependencies are architectural concerns, not compilation-level. |
| Capability | ✗ | ✗ | ✓ (Gen-C `CapabilityResolutionPass`; 13+ capabilities) | ✓ (R1-B D08: `compiler.backend.capabilities`) | **MIGRATE (minimal)** | The canonical `CompilerBackend` Protocol declares capabilities. The canonical IR should also declare required capabilities. Add `CompilationPlan.required_capabilities: list[str]`. |
| Backend constraints | ✗ | ✗ | (implied) | ✓ (R1-B D07 §6) | **MIGRATE** | Add `CompilationPlan.backend_constraints: list[str]`. |

**Summary:** 3 relationships retained; 1 migration (Service.security); 2 migrations (capabilities, backend constraints); 1 defer (service-service dependency).

---

## 4. Identity and hashing comparison

| Aspect | `CompilationPlan` | `BIR` | Gen-C | R1-B D07 | Action | Reason |
|---|---|---|---|---|---|---|
| Content hash | ✗ (no hash on plan itself) | ✗ (no hash) | ✗ | ✓ (canonical) | **MIGRATE** | Add `content_hash` to `CompilationPlan`. SHA-256 over canonical JSON. Per R1-B D07 §6, the canonical Compiler IR has a content hash. |
| Deterministic identity | ✗ (plan_id is derived from ISR hash, not from plan itself) | ✗ | ✗ | ✓ (canonical) | **MIGRATE** | The canonical Compiler IR's identity is its content hash. The plan_id is a derived identifier. |
| Serialization | `plan.model_dump()` (Pydantic) | (no canonical serialization) | (no canonical serialization) | ✓ (deterministic JSON) | **MIGRATE** | The canonical Compiler IR has a deterministic serialization. Use sorted-key JSON. |
| Schema version | ✗ | ✗ | ✗ | ✓ (`schema_version` field) | **MIGRATE** | Add `schema_version` field (semantic versioning). |

**Summary:** 4 identity/hashing migrations required for `CompilationPlan` to become the canonical Compiler IR contract.

---

## 5. Validation comparison

| Aspect | `CompilationPlan` | `BIR` | Gen-C | R1-B D07 | Action | Reason |
|---|---|---|---|---|---|---|
| Fail-closed construction | ✓ (Pydantic frozen) | ✓ (frozen dataclass) | ✗ (fail-open at validation, verification) | ✓ (canonical) | **CANONICALIZE** | The canonical Compiler IR is fail-closed. Gen-C is fail-open; on retirement. |
| Invariants | ✗ (no invariants) | ✗ | ✗ | ✓ (canonical) | **MIGRATE** | Add invariants to the canonical Compiler IR. |
| Required fields | ✓ (Pydantic min_length) | ✓ (frozen) | ✓ | ✓ (canonical) | **RETAIN CANONICAL** | |

**Summary:** The canonical `CompilationPlan` has fail-closed construction (Pydantic frozen) but no semantic invariants. Gen-C is fail-open at multiple points. The canonical Compiler IR contract must add semantic invariants.

---

## 6. Failure semantics comparison

| Failure mode | `CompilationPlan` | `BIR` | Gen-C | R1-B D14 | Action | Reason |
|---|---|---|---|---|---|---|
| Invalid input | Pydantic raises `ValidationError` | (no validation) | Fail-open at validation pass | ✓ (canonical) | **RETAIN CANONICAL** | Pydantic's built-in validation is the canonical fail-closed mechanism. |
| Backend unsupported feature | Backend returns empty repo | (no mechanism) | (no mechanism) | ✓ (`UNSUPPORTED_CAPABILITY` → `Verification INDETERMINATE`) | **RETAIN CANONICAL** | The cross-contract mapping (D14) is the canonical rule. |
| Lowering failure | (pure function; raises on bad input) | (no mechanism) | Fail-open (PassManager continues) | ✓ (canonical) | **RETAIN CANONICAL** | The canonical runtime's `isr_to_plan` is a pure function that raises on bad input. The PassManager is on the retirement path. |

---

## 7. Provenance comparison

| Aspect | `CompilationPlan` | `BIR` | Gen-C | R1-B D07 | Action | Reason |
|---|---|---|---|---|---|---|
| Source ISR identity | ✓ (`isr_id` field) | ✗ (no field) | (implied by lowering pass) | ✓ (canonical) | **RETAIN CANONICAL** | |
| Source Architecture identity | ✗ (no field) | ✗ | (implied) | ✓ (canonical; "source_architecture_candidate_reference") | **MIGRATE** | Add `source_architecture_candidate_id: str | None` to `CompilationPlan`. |
| Provenance metadata | ✗ | ✗ | (unstructured `metadata: dict`) | ✓ (canonical; "lowering operator, timestamp, lowering chain") | **MIGRATE** | Add `lowering_operator: str`, `lowering_timestamp: str`, `lowering_chain: list[str]`. |
| Backend identity | (in `BackendIdentity`) | ✗ | (in `BackendResult`) | ✓ (canonical) | **RETAIN CANONICAL** | The backend identity is at the backend boundary, not the IR. |

---

## 8. Backend compatibility comparison

| Aspect | `CompilationPlan` | `BIR` | Gen-C | R1-B D08 | Action | Reason |
|---|---|---|---|---|---|---|
| `backend_constraints` | ✗ | ✗ | (implied) | ✓ (canonical) | **MIGRATE** | Add `backend_constraints: list[str]`. |
| Capabilities | ✗ | ✗ | ✓ (Gen-C `CapabilityResolutionPass`) | ✓ (canonical; `compiler.backend.capabilities`) | **MIGRATE (minimal)** | Add `required_capabilities: list[str]`. |
| `UNSUPPORTED_CAPABILITY` outcome | (at backend level) | (at backend level) | (at backend level) | ✓ (canonical; D14) | **RETAIN CANONICAL** | The cross-contract mapping is canonical. |

---

## 9. Field classification (semantic/derived/observational)

| Field | Class | Reason |
|---|---|---|
| `plan_id` | derived (from ISR hash) | |
| `isr_id` | semantic | Identifies the source ISR |
| `services[].id` | semantic | |
| `services[].name` | semantic | |
| `services[].data_models` | semantic | |
| `services[].published_events` | semantic | |
| `services[].consumed_events` | semantic | |
| `security[].policy_id` | semantic | |
| `content_hash` (to be added) | derived | SHA-256 over canonical serialization |
| `schema_version` (to be added) | semantic | Versioning |
| `source_architecture_candidate_id` (to be added) | semantic | Lineage |
| `lowering_operator` (to be added) | observational metadata | |
| `lowering_timestamp` (to be added) | observational metadata | |
| `lowering_chain` (to be added) | observational metadata | |
| `required_capabilities` (to be added) | semantic | |
| `backend_constraints` (to be added) | semantic | |
| `services[].security` (to be added) | semantic | |

---

## 10. Compatibility verdict

The canonical `CompilationPlan` is the **closest existing candidate** for the canonical Compiler IR, but it is **incomplete**:

- It has 4 of the required node types (Service, DataModel, Event, SecurityPolicy). The canonical contract (D07) requires 15+ node concepts (component model, interfaces, operations, data structures, data relationships, service boundaries, dependencies, contracts, execution relationships, configuration, deployment, capabilities, resources, security, observability).
- It is missing content-hash, schema version, provenance, backend constraints, capabilities, security edges.
- It has no semantic invariants.
- It is not a `compiler.core.canonical_ir` module; it lives in `compiler.core.plan` as a stabilization implementation.

The canonical Compiler IR is a **future module** (e.g., `compiler/core/canonical_ir.py`) that subsumes the current `CompilationPlan` and adds the missing fields. The current `CompilationPlan` is the **stabilization** implementation that the campaign runtime depends on.

**Recommendation:** The canonical Compiler IR contract is **extended** (D07 refinement) to add the missing fields. The current `CompilationPlan` is **not deprecated**; it is the stabilization implementation. A new `CanonicalCompilerIR` Pydantic model is created in R1-D.2 (or a future R-phase) that subsumes `CompilationPlan` and adds the missing fields. The campaign runtime migrates to the canonical Compiler IR in R1-D.5.

---

## 11. R1-B D07 contract review

The R1-B D07 contract (`folder/CONTRACT_CanonicalCompilerIR.md`) was reviewed. It is **authoritative** but **incomplete** relative to the R1-D.2 analysis. The contract should be **refined** to add:

- `source_architecture_candidate_id` (lineage)
- `lowering_operator`, `lowering_timestamp`, `lowering_chain` (provenance)
- `required_capabilities` (backend compatibility)
- `backend_constraints` (backend compatibility)
- `services[].security` (security edges; currently missing)
- `content_hash` (identity)
- `schema_version` (versioning)

These additions are **not a fundamental contract change**; they are **field additions** consistent with the existing D07 contract. The D07 contract is refined in D2-D4 (the next deliverable).

---

## 12. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D2: `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md`
- D2-D4: `folder/CONTRACT_CanonicalCompilerIR.md` (next; refinement)
- D2-D5: `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md`
- D07 (R1-B): `folder/CONTRACT_CanonicalCompilerIR.md`

---

*End of D2-D3. The R1-D.2 semantic comparison is complete. The canonical `CompilationPlan` is incomplete relative to the D07 contract. 4 node types retained, 7 deferred, 1 rejected. 4 identity/hashing migrations required. 1 service-security migration. The D07 contract is refined in D2-D4.*
