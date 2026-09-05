# CONTRACT_CanonicalCompilerIR (R1-B D07 + R1-D.2 D2-D4 refinement)

**Contract:** `CompilerIR`
**Status:** R1-B Deliverable D07 (authoritative) + R1-D.2 Deliverable D2-D4 (refinement). The D2-D4 refinement adds 8 fields (content_hash, schema_version, source_architecture_candidate_content_hash, backend_constraints, required_capabilities, lowering_metadata, provenance, deterministic_serialization) and refines 3 fields (compilation_id, source_isr_reference, security_requirements). The D07 original text is preserved below; the D2-D4 refinement is at the bottom.
**Canonical owner:** (D07 defines; stabilization is `compiler/core`; future canonical Compiler IR module is R1-D.5)

**Invariants this contract satisfies:** INV-B05 (Compiler IR is distinct from ISR), INV-B06 (Compiler IR is distinct from generated artifacts), INV-B14 (no category-specific compiler becomes a new architectural authority).

---

# Part I: R1-B D07 original contract (authoritative; preserved)

## 1. Purpose

The `CompilerIR` is the compiled, technology-neutral representation of an architecture, ready for backend lowering. It is **distinct from ISR** (D03), **distinct from Architecture Model** (D04), and **distinct from generated artifacts** (D09).

## 2. The R1-A C-03 refinement (mandatory)

```text
Canonical ISR
      ↓
Architecture Model
      ↓
Compiler IR
      ↓
Backend Lowering
      ↓
ArtifactSet
```

`CompilationPlan` (the current stabilization implementation at `compiler/core/plan.py`) is **not** the final architectural definition of `CompilerIR`. The contract defines the future CompilerIR independently of `CompilationPlan`. The canonical CompilerIR module is created in a future R-phase (R1-D.5).

**BIR is a semantic donor, not a competing IR.** The 9 BIRNodeTypes (`HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`) are read as references; the genuinely-semantic ones are absorbed into the canonical CompilerIR contract where appropriate. BIR is not modified; the canonical CompilerIR is a new module.

**Content-hash is added to the canonical CompilerIR, not to BIR.** This prevents BIR from accidentally becoming canonical via the stabilization layer.

## 3. Architecture (D07)

The canonical CompilerIR carries:

- compilation identity
- source ISR / architecture references
- target requirements
- component model
- interfaces
- data flows
- persistence requirements
- API contracts
- frontend / backend responsibilities
- security requirements
- deployment requirements
- observability requirements
- backend constraints
- lowering metadata
- provenance
- deterministic identity / hash

## 4. Identity (D07)

- **Compilation ID:** UUIDv5 over the canonical serialization.
- **Content hash:** SHA-256 over canonical serialization. The hash is the IR's identity.

## 5. Lifecycle and mutability (D07)

- **Frozen.** Each compilation is a new identity; the previous is immutable.
- **Append-only per compilation.**

## 6. Required fields (D07)

| Field | Required? | Classification |
|---|---|---|
| Compilation ID | yes | **semantic** (identity) |
| Source ISR revision reference (content hash) | yes | **semantic** |
| Source ArchitectureCandidate reference (content hash) | yes | **semantic** |
| Target requirements (links to RequirementGraph IDs) | yes | **semantic** |
| Component model | yes | **semantic** |
| Interfaces | yes | **semantic** |
| Data flows | yes | **semantic** |
| Persistence requirements | yes | **semantic** |
| API contracts | yes | **semantic** |
| Frontend / backend responsibilities | yes | **semantic** |
| Security requirements | yes | **semantic** |
| Deployment requirements | yes | **semantic** |
| Observability requirements | yes | **semantic** |
| Backend constraints (which backends can lower this IR) | yes | **semantic** |
| Lowering metadata (lowering operator, timestamp) | yes | **observational metadata** |
| Provenance (source ISR hash, source architecture hash, lowering chain) | yes | **observational metadata** |
| Serialization (deterministic JSON) | yes | **derived** |
| Content hash (SHA-256) | yes | **derived** |

## 7. Field classification (D07)

| Field | Classification |
|---|---|
| All component, interface, data-flow, persistence, API, security, deployment, observability, backend-constraint fields | **semantic** |
| Source ISR / architecture references | **semantic** (non-derivable) |
| Serialization, hashing | **derived** |
| Lowering metadata, timestamps, provenance | **observational metadata** |

## 8. Hashing and serialization (D07)

- **Serialization:** deterministic JSON.
- **Hashing:** SHA-256 over canonical serialization. The hash is the IR's identity.
- **Provenance hash:** the content hash of the Provenance carrier is included in the IR's content hash.

## 9. Provenance (D07)

- Source ISR revision content hash.
- Source ArchitectureCandidate content hash.
- Lowering operator identity.
- Lowering timestamp.
- Lowering chain (the sequence of lowering operations that produced this IR).

## 10. Failure semantics (D07)

- Lowering that produces a non-traceable IR (no provenance to ISR/Architecture) is rejected.
- An IR with `status=LOWERING_OK` and empty component model is forbidden (the lowering did something).
- The contract distinguishes:
  - `LOWERING_OK` — IR produced.
  - `LOWERING_FAILED` — lowering failed; no IR produced; reason recorded.
  - `LOWERING_BLOCKED` — a precondition (e.g. ISR invariant violation) was not met; no IR produced.
  - `LOWERING_INDETERMINATE` — operator could not determine the IR deterministically; reason recorded.

## 11. Extension mechanism (D07)

- New IR node types require an ADR; do not add them via the contract surface.
- New fields (e.g. additional observability kinds) require an ADR.
- The contract surface is frozen; extensions are versioned.

## 12. Current implementation (stabilization, D07)

`compiler/core/plan.py:CompilationPlan` (Pydantic flat: `Service`, `DataModel`, `Event`, `SecurityPolicy`). Used by `certification/`. The stabilization implementation is **not** the final canonical contract; the canonical CompilerIR module is created in a future R-phase.

## 13. Legacy implementations (D07)

- `constitutional_architecture/compiler/bir/model.py:BIR` (BIRNodeType: `HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`). **LEGACY.** Treated as a semantic donor, not a competing IR. The 9 BIRNodeTypes are read as references; genuinely-semantic ones are absorbed into the canonical CompilerIR contract where appropriate. Retired as runtime per a future R-phase.
- `UniversalISR`-as-typed-graph (consumed by `constitutional_architecture/compilers/*`). **LEGACY.** Retired as runtime per a future R-phase.

## 14. Migration destination (D07)

- Legacy `BIR` → LEGACY classification; 9 BIRNodeTypes selectively absorbed as references into the canonical CompilerIR contract; BIR is **not** modified to add content-hash; the canonical CompilerIR is a new module with its own content-hash.
- Legacy `UniversalISR`-as-typed-graph → LEGACY; retired as runtime.

---

# Part II: R1-D.2 D2-D4 refinement

**Refinement authority:** R1-D.2 master prompt §16 (D2.5). The R1-D.2 analysis (D2-D3) identified that the D07 contract is complete in principle but incomplete in practice — the current `CompilationPlan` lacks several fields the D07 contract requires. This refinement extends the D07 contract with the missing fields, consistent with the D07 architecture and intent.

## 15. Refinement summary

| Action | Count | Fields |
|---|---|---|
| RETAIN | 3 | Component model, Data flows, Persistence requirements |
| REFINE | 3 | Compilation ID, Source ISR reference, Security requirements |
| ADD | 8 | Content hash, Schema version, Source ArchitectureCandidate reference, Backend constraints, Required capabilities, Lowering metadata, Provenance, Serialization |
| DEFER | 6 | Target requirements, Interfaces, API contracts, Frontend/backend responsibilities, Deployment requirements, Observability requirements |

## 16. Refined fields (D2-D4)

### 16.1 Identity (refined)

- **Compilation ID:** Content-hash-derived (SHA-256 over canonical serialization). The `plan_id` field is preserved for backward compatibility with the current `CompilationPlan`.
- **Content hash:** SHA-256 over canonical serialization. The hash is the IR's identity.

### 16.2 Source ISR revision reference (refined)

The current `CompilationPlan.isr_id` carries the ISR's `system_id`, not the `content_hash`. The refined field must carry the **content hash** (per D07 §6 "Source ISR revision reference (content hash)"). The future canonical Compiler IR module must add `source_isr_content_hash: str`.

### 16.3 Security requirements (refined)

The current `CompilationPlan` has `security: list[SecurityPolicy]` (top-level). The D07 contract requires security to be expressible **per service** (a service is secured by a security policy). The future canonical Compiler IR must add `Service.security: list[SecurityPolicy]`.

### 16.4 Source ArchitectureCandidate reference (added)

| Field | Required? | Classification |
|---|---|---|
| `source_architecture_candidate_content_hash: str | None` | yes | **semantic** (lineage) |

### 16.5 Content hash (added)

| Field | Required? | Classification |
|---|---|---|
| `content_hash: str` (SHA-256, 64 hex chars) | yes | **derived** |

The canonical Compiler IR has its own content hash, independent of the source ISR's content hash. The `isr_to_plan` function preserves the source ISR hash via `isr_id`, but the plan's own content hash is computed from the plan's canonical serialization.

### 16.6 Schema version (added)

| Field | Required? | Classification |
|---|---|---|
| `schema_version: str` (semver, e.g. "1.0") | yes | **semantic** |

### 16.7 Backend constraints (added)

| Field | Required? | Classification |
|---|---|---|
| `backend_constraints: list[str]` (backend IDs that can lower this IR) | yes | **semantic** |

### 16.8 Required capabilities (added)

| Field | Required? | Classification |
|---|---|---|
| `required_capabilities: list[str]` (capability IDs required; from Gen-C `CapabilityResolutionPass`) | yes | **semantic** |

### 16.9 Lowering metadata (added)

| Field | Required? | Classification |
|---|---|---|
| `lowering_operator: str` (identity of the lowering function) | yes | **observational metadata** |
| `lowering_timestamp: str` (ISO8601) | yes | **observational metadata** |
| `lowering_chain: list[str]` (sequence of lowering operations) | yes | **observational metadata** |

### 16.10 Provenance (added)

| Field | Required? | Classification |
|---|---|---|
| `source_isr_content_hash: str` (refined from `isr_id`) | yes | **semantic** |
| `source_architecture_content_hash: str | None` (added) | yes | **semantic** |
| `lowering_chain: list[str]` (added) | yes | **observational metadata** |

### 16.11 Serialization (added)

| Field | Required? | Classification |
|---|---|---|
| Deterministic JSON serialization (sorted keys, UTF-8) | yes | **derived** |

The current Pydantic `model_dump()` is not deterministic by default. The canonical Compiler IR must use a canonical serialization (sorted keys, no default-str anti-pattern, UTF-8).

## 17. Deferred fields (not in the canonical IR, by design)

Per D2-D3, the following fields are **deferred** (not part of the canonical IR):

- **Target requirements:** upstream of the IR; preserved via ISR lineage.
- **Interfaces:** the canonical IR expresses interfaces via API contracts (deferred to a future R-phase).
- **API contracts:** deferred to a future R-phase.
- **Frontend / backend responsibilities:** the canonical IR is technology-neutral; frontend/backend is a backend concern.
- **Deployment requirements:** deployment is a D09 ArtifactSet + D10 RuntimeObservation concern.
- **Observability requirements:** observability is a D12 concern.

## 18. Migration strategy

The R1-D.2 refinements are applied to the canonical Compiler IR module (a future R-phase implementation, R1-D.5). The current `CompilationPlan` remains the stabilization implementation until the canonical Compiler IR module is created.

1. **R1-D.2 (this phase):** Refine the D07 contract (this addendum). No code changes to `CompilationPlan`.
2. **R1-D.5 (future):** Create the canonical Compiler IR module (e.g., `compiler/core/canonical_ir.py`) that implements the refined D07 contract (including the 8 new fields). The canonical Compiler IR subsumes `CompilationPlan` with a `from_plan(plan: CompilationPlan) -> CanonicalCompilerIR` migration function. The campaign runtime migrates from `CompilationPlan` to `CanonicalCompilerIR`.
3. **R1-D.5 (future):** Retire the per-category compilers, Gen-C pipeline, and BIR.

## 19. Compatibility impact

| Aspect | Impact |
|---|---|
| Campaign runtime (Tier A) | None. `CompilationPlan` is unchanged. |
| `certification/campaign/*` | None. `plan.model_dump()` is preserved. |
| `certification/provenance/bundle.py:116` | None. The SHA-256 hash is preserved. |
| B3-v2 evidence | None. The plan_id derivation is preserved. |
| R1-D.2 tests | New tests for the contract refinements (D2-D5). |

## 20. Field classification (D2-D4 refined)

| Field | Classification |
|---|---|
| Component model, Data flows, Persistence requirements | **semantic** (D07 retained) |
| Compilation ID (refined to content-hash-derived) | **semantic** |
| Source ISR revision reference (content hash; refined) | **semantic** |
| Source ArchitectureCandidate reference (content hash; added) | **semantic** |
| Security requirements (refined: per-service) | **semantic** |
| Backend constraints (added) | **semantic** |
| Required capabilities (added) | **semantic** |
| Schema version (added) | **semantic** |
| Content hash (added) | **derived** |
| Serialization (added) | **derived** |
| Lowering metadata (added) | **observational metadata** |
| Provenance (added/refined) | **observational metadata** |

## 21. Cross-references

- D07 (R1-B): original contract (Part I above; authoritative).
- D2-D3: `folder/R1_D2_COMPILER_IR_SEMANTIC_COMPARISON.md` (the analysis that motivated this refinement).
- D2-D5: `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md` (next; the migration actions for each refinement).
- D2-D8: `folder/R1_D2_CANONICAL_COMPILER_INTEGRATION_REPORT.md` (the integration plan).
- D2-D10: `folder/R1_D2_GATE_REPORT.md` (the R1-D.2 gate report).

---

*End of contract. Part I (R1-B D07) is authoritative. Part II (R1-D.2 D2-D4) refines Part I with 8 new fields and 3 refinements. The current `CompilationPlan` is the stabilization implementation; the future canonical Compiler IR module is R1-D.5.*
