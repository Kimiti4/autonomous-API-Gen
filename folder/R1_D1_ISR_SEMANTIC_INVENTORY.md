# R1_D1_ISR_SEMANTIC_INVENTORY (R1-D.1 D1)

**Status:** R1-D.1 Deliverable D1. Canonical ISR semantic inventory. Index: `folder/CONTRACT_CanonicalISR.md` (D03), `folder/R1_B_CONTRACT_GATE_REPORT.md` (D20), `folder/R1_C_GATE_REPORT.md` (C12).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

**Method:** File:line-cited enumeration of every ISR-related implementation, schema, adapter, serializer, validator, factory, consumer, and test. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

**Scope:** R1-D.1 ONLY. R1-D.2 (Compiler IR) and R1-D.3 (Evolution/EIR) are HARD-STOPPED.

---

## 0. Inventory scope

The R1-D.1 master prompt requires inventorying:

- All ISR implementations.
- All ISR schemas, adapters, serializers, validators, factories.
- All ISR consumers.
- All ISR tests.

The inventory covers:

1. Canonical ISR (Section 1).
2. Constitutional ISR implementations (Section 2).
3. Constitutional ISR semantics (validators) (Section 3).
4. Constitutional ISR supporting infrastructure (serialization, versioning, diff, metrics, completeness) (Section 4).
5. Constitutional ISR views and profiles (Section 5).
6. Constitutional IRR (Requirement representation under `constitutional_architecture/isr/irr/`) (Section 6).
7. Third ISR model (`constitutional_architecture/core/models/isr.py:UniversalISR`) (Section 7).
8. Canonical ISR consumers (Section 8).
9. Tests (Section 9).

---

## 1. Canonical ISR (`isr/core/`)

### 1.1 Files

| File | Size | Purpose |
|---|---|---|
| `isr/__init__.py` | 543B | Package init; exports `ISRRevision`, `ISRGraph`, `Node`, `Edge`, `Provenance`, `compute_content_hash`, `validate_invariants` |
| `isr/core/graph.py` | 2,763B | Typed directed graph: `NodeType` (9 values), `EdgeType` (8 values), `Node`, `Edge`, `ISRGraph`, `EDGE_TYPE_COMPATIBILITY` matrix |
| `isr/core/identity.py` | 2,099B | `Provenance` (frozen Pydantic) and `compute_content_hash` (SHA-256 over canonical sorted JSON) |
| `isr/core/invariants.py` | 4,762B | `ISRInvariantViolation`; `FORBIDDEN_IMPLEMENTATION_TERMS` (25 terms); `validate_invariants` (fail-closed) |
| `isr/core/revision.py` | 1,776B | `ISRRevision` (frozen Pydantic, content-hashed); `create()` factory |

### 1.2 NodeType taxonomy (9 values)

| NodeType | Value | Semantic |
|---|---|---|
| `DOMAIN` | "domain" | A bounded context or problem domain |
| `CAPABILITY` | "capability" | A system capability (verb-noun) |
| `SERVICE` | "service" | A service that exposes capabilities |
| `API` | "api" | An API surface |
| `DATA_MODEL` | "data_model" | A data model (entity or aggregate) |
| `EVENT` | "event" | A domain event |
| `SECURITY_POLICY` | "security_policy" | A security policy (authn, authz, secret handling) |
| `INFRASTRUCTURE_TARGET` | "infrastructure_target" | A deployment/infra intent (not a concrete tech) |
| `REQUIREMENT_REF` | "requirement_ref" | A reference back to a RequirementGraph node |

### 1.3 EdgeType taxonomy (8 values)

| EdgeType | Value | Semantic |
|---|---|---|
| `SATISFIES` | "satisfies" | source (CAPABILITY) satisfies target (REQUIREMENT_REF) |
| `IMPLEMENTED_BY` | "implemented_by" | source is implemented by target |
| `EXPOSES` | "exposes" | source (SERVICE) exposes target (API) |
| `PERSISTS` | "persists" | source (SERVICE/API) persists target (DATA_MODEL) |
| `PUBLISHES` | "publishes" | source (SERVICE) publishes target (EVENT) |
| `CONSUMED_BY` | "consumed_by" | source (EVENT) is consumed by target (SERVICE/API) |
| `DEPENDS_ON` | "depends_on" | source depends on target |
| `SECURED_BY` | "secured_by" | source is secured by target (SECURITY_POLICY) |

### 1.4 Identity and hashing

- `Provenance` (frozen Pydantic): `parent_revision_id`, `requirement_refs`, `derivation_refs`, `created_by`, `created_at` (ISO8601).
- `compute_content_hash(schema_version, graph)`: SHA-256 over canonical JSON with sorted keys, sorted node/edge IDs, UTF-8 encoding. Deterministic.
- `ISRRevision.content_hash`: 64 hex chars (SHA-256).
- `ISRRevision.create()`: factory that calls `validate_invariants` then computes `content_hash`.

### 1.5 Invariants (fail-closed)

- No duplicate edge IDs (`isr/core/invariants.py:57-60`).
- Referential integrity: every edge references existing nodes (`isr/core/invariants.py:64-71`).
- Edge type compatibility: `EDGE_TYPE_COMPATIBILITY` matrix enforced (`isr/core/invariants.py:76-90`).
- Implementation leakage: 25 forbidden terms checked on all string values in node/edge properties (`isr/core/invariants.py:130-137`).
- `REQUIREMENT_REF` nodes must carry a non-empty string `ref_id` (`isr/core/invariants.py:98-105`).

### 1.6 Canonical owner

`isr/core/`. The canonical contract is D03 (R1-B).

---

## 2. Constitutional ISR implementations

### 2.1 `constitutional_architecture/isr/model/isr.py:ISR`

| Field | Value |
|---|---|
| File | `constitutional_architecture/isr/model/isr.py:67-144` |
| Type | `@dataclass(frozen=True)` |
| Root | `System` (rich model) |
| Provenance | `ISRProvenance` (`created_at`, `created_by`, `parent_hash`, `mutation_description`, `evolution_run_id`, `generation`) |
| Identity | `content_hash` (property, projects only `system` via `semantic_content_hash`) |
| `with_system()` | creates new ISR with incremented version |
| `validate_structure()` | calls 12 semantic validators (Section 3) |
| Status | **LEGACY** (per R1-A + R1-B D17 L01) |
| Used by | `constitutional_architecture/` only (not the canonical campaign runtime) |

### 2.2 Constitutional `System` model

| Field | Value |
|---|---|
| File | `constitutional_architecture/isr/model/system.py:34-103` |
| Type | `@dataclass(frozen=True)` |
| Carries | `modules`, `deployment`, `metadata`, `global_policies`, `business_capabilities`, `reliability_requirements`, `architectural_boundaries`, `requirements`, `acceptance_criteria`, `deployment_intents`, `testing_anchors`, `documentation_intents`, `evolution_objectives`, `protected_regions`, `evolution_policies`, `architectural_decisions`, `security_threats`, `constraints` |
| NodeType | 19 values (SYSTEM, MODULE, ENTITY, SERVICE, WORKFLOW, POLICY, INTERFACE, EVENT, DEPLOYMENT, CONSTRAINT, FIELD, OPERATION, STATE, TRANSITION, RULE, PERMISSION, ENDPOINT, CONFIGURATION, DOCUMENTATION, TEST_STRATEGY) |
| EdgeType | 16 values (OWNS, DEPENDS_ON, EMITS, CONSUMES, REFERENCES, IMPLEMENTS, SECURED_BY, DEPLOYS_TO, ORCHESTRATES, CONSTRAINS, CONTAINS, TRANSITIONS_TO, TRIGGERS, VALIDATES, DOCUMENTS, TESTS) |
| Status | **LEGACY** (per R1-A + R1-B D17 L01) |

### 2.3 `constitutional_architecture/core/models/isr.py:UniversalISR`

| Field | Value |
|---|---|
| File | `constitutional_architecture/core/models/isr.py:58-104` |
| Type | Pydantic `BaseModel` |
| NodeType | 17 values (DOMAIN, DATA_ENTITY, DATA_ATTRIBUTE, CAPABILITY, SERVICE, COMPONENT, API_ENDPOINT, EVENT, FRONTEND_VIEW, SECURITY_POLICY, TENANCY_POLICY, RETENTION_POLICY, AUDIT_POLICY, INFRA_REQUIREMENT, OPERATIONAL_POLICY, SLO_DEFINITION, TELEMETRY_REQUIREMENT) |
| EdgeType | 13 values (OWNS, IMPLEMENTS, EXPOSES, EMITS, CONSUMES, DEPENDS_ON, SECURES, PERSISTS, RENDERS, HAS_ATTRIBUTE, RELATES_TO, GOVERNED_BY, MONITORS) |
| Used by | `constitutional_architecture/compilers/*` (per-category compilers; L10 RETIRE) |
| Status | **LEGACY** (per R1-A + R1-B D17 L02) |

---

## 3. Constitutional ISR semantics (validators)

The constitutional ISR's `validate_structure()` (`constitutional_architecture/isr/model/isr.py:112-144`) calls 12 semantic validators. Each is a genuinely-semantic check on the rich `System` model.

| # | Validator | Module | Lines | Semantic |
|---|---|---|---|---|
| 1 | `validate_module_temporal_constraints` | `constitutional_architecture/isr/semantics/temporal.py` | (6,799B module) | Module temporal constraints |
| 2 | `validate_module_migration_constraints` | `constitutional_architecture/isr/semantics/migration.py` | (9,072B module) | Module migration constraints |
| 3 | `validate_system_capability_constraints` | `constitutional_architecture/isr/semantics/capability.py` | (6,040B module) | System capability constraints |
| 4 | `validate_system_reliability_constraints` | `constitutional_architecture/isr/semantics/reliability.py` | (10,611B module) | Reliability requirements |
| 5 | `validate_system_boundary_constraints` | `constitutional_architecture/isr/semantics/boundary.py` | (7,607B module) | Architectural boundaries |
| 6 | `validate_system_requirement_constraints` | `constitutional_architecture/isr/semantics/requirement.py` | (10,447B module) | Requirement traceability |
| 7 | `validate_system_deployment_constraints` | `constitutional_architecture/isr/semantics/deployment.py` | (8,747B module) | Deployment intent |
| 8 | `validate_system_documentation_constraints` | `constitutional_architecture/isr/semantics/documentation.py` | (7,331B module) | Documentation intent |
| 9 | `validate_system_evolution_policy_constraints` | `constitutional_architecture/isr/semantics/evolution_policy.py` | (16,079B module) | Evolution policy |
| 10 | `validate_system_decision_constraints` | `constitutional_architecture/isr/semantics/decision.py` | (11,337B module) | Architectural decisions |
| 11 | `validate_system_threat_constraints` | `constitutional_architecture/isr/semantics/threat.py` | (11,270B module) | Security threat obligations |
| 12 | `validate_system_testing_anchor_constraints` | `constitutional_architecture/isr/semantics/testing_anchor.py` | (8,145B module) | Testing anchor constraints |

Additional semantics files:

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/isr/semantics/application_identity.py` | 595B | Application identity |
| `constitutional_architecture/isr/semantics/projection.py` | 4,301B | `semantic_content_hash`, `canonical_form`, `canonicalize` |

**Total: 12 validators + 2 supporting modules (projection, application_identity).**

### 3.1 Classification of validators for R1-D.1 migration

| Validator | MIGRATE? | Reason |
|---|---|---|
| `requirement.py` | **MIGRATE** | Requirements are semantic obligations, not test mechanisms. Applicable to canonical `REQUIREMENT_REF` nodes. |
| `testing_anchor.py` | **MIGRATE** | Testing anchors are semantic, not test-mechanism-specific. Applicable to canonical ISR. |
| `threat.py` | **MIGRATE** | Security threats are semantic obligations. Applicable to canonical `SECURITY_POLICY` nodes with `SECURED_BY` edges. |
| `boundary.py` | **ALREADY CANONICAL** | `EDGE_TYPE_COMPATIBILITY` matrix is the canonical architectural boundary. No migration needed. |
| `projection.py` | **ALREADY CANONICAL** | `compute_content_hash` is the canonical semantic content hash. The constitutional `semantic_content_hash` aligns with the canonical approach. |
| `capability.py` | **MIGRATE (minimal)** | Capability constraints are semantic. Applicable to canonical `CAPABILITY` nodes. |
| `deployment.py` | **MIGRATE (minimal)** | Deployment intent is semantic. Applicable to canonical `INFRASTRUCTURE_TARGET` nodes. |
| `temporal.py` | **DEFER** | Temporal constraints are not in the canonical ISR's flat 9-node/8-edge model. |
| `migration.py` | **DEFER** | Module migration is not in the canonical ISR's flat model. |
| `reliability.py` | **DEFER** | Reliability requirements are not in the canonical ISR's flat model. |
| `documentation.py` | **DEFER** | Documentation intent is not in the canonical ISR's flat model. |
| `evolution_policy.py` | **DEFER** | Evolution policy is not in the canonical ISR's flat model. |
| `decision.py` | **DEFER** | Architectural decisions are not in the canonical ISR's flat model. |
| `application_identity.py` | **DEFER** | Application identity is not in the canonical ISR's flat model. |

**Summary:**
- 5 MIGRATE (requirement, testing_anchor, threat, capability, deployment).
- 2 ALREADY CANONICAL (boundary, projection).
- 7 DEFER (temporal, migration, reliability, documentation, evolution_policy, decision, application_identity).

---

## 4. Constitutional ISR supporting infrastructure

### 4.1 Serialization

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/isr/serialization/*` | (directory) | Serialization for the rich ISR model |

### 4.2 Versioning

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/versioning/*` | `LineageTracker`, `ContentHasher`, version management |

### 4.3 Diff

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/isr/diff/*` | (directory) | `StructuralDiff`, `SemanticDiff` |

### 4.4 Metrics

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/isr/metrics/*` | (directory) | `StaticFitnessEvaluator` |

### 4.5 Completeness

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/completeness/*` | `CompletenessChecker` |

### 4.6 Graph

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/isr/graph/*` | (directory) | `TypedGraph` (separate from canonical `isr/core/graph.py`) |
| `constitutional_architecture/isr/isr_graph.py` | 27,457B | `ISRGraph` (constitutional; distinct from canonical) |
| `constitutional_architecture/isr/legacy_model.py` | 27,936B | Legacy ISR model |

**Status:** All LEGACY. Per R1-A + R1-B D17 L01, L03, L04, L05, L06.

---

## 5. Constitutional ISR views and profiles

### 5.1 Views

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/views/*` | Views over the rich ISR model |

**Status:** DEFER (out of R1 scope; views are not part of the Full-Stack Compiler vertical slice).

### 5.2 Profiles

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/profiles/*` | Architecture profiles |

**Status:** DEFER (out of R1 scope).

---

## 6. Constitutional IRR (Requirement representation)

### 6.1 `constitutional_architecture/isr/irr/`

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/irr/requirement.py` | `Requirement` model (rich) |
| `constitutional_architecture/isr/irr/graph.py` | Requirement graph (rich) |
| `constitutional_architecture/isr/irr/extraction.py` | Requirement extraction |
| `constitutional_architecture/isr/irr/model.py` | IRR model |

**Status:** MIGRATE_SEMANTICS (per R1-C C01 §1.42). The semantic concept of requirement representation is captured; the canonical RequirementGraph (D02) is the authoritative contract.

---

## 7. Third ISR model

### 7.1 `constitutional_architecture/core/models/isr.py:UniversalISR`

Already documented in Section 2.3. **Status:** LEGACY (RETIRE per R1-D.5).

---

## 8. Canonical ISR consumers

### 8.1 Direct importers of `isr/core/*`

| Path | Imports | Purpose |
|---|---|---|
| `isr/ports/{reader,store}.py` | `isr.core.revision.ISRRevision` | ISR port abstractions |
| `isr/adapters/inmemory.py` | `isr.core.*` | In-memory adapter |

### 8.2 Direct importers of `isr.*` (non-core)

| Path | Imports | Purpose |
|---|---|---|
| `certification/campaign/plan_builder.py:19-20` | `isr.core.identity.compute_content_hash`, `isr.core.revision.ISRRevision` | Campaign plan builder (canonical runtime) |
| `evolution/core/{engine,construction,fitness_evaluator,materialize}.py` | `isr.core.graph.*`, `isr.core.revision.ISRRevision` | Evolution engine (canonical) |
| `genesis/mapper.py:8`, `genesis/validator.py:7-9` | `isr.core.*` | Genesis subsystem |
| `tests/cbc1/*`, `tests/v12/*`, `tests/v13/*`, `tests/v14/*`, `tests/test_isr_substrate_v12.py` | `isr.core.*` | ISR tests |

### 8.3 Direct importers of `constitutional_architecture/isr/*`

| Path | Imports | Purpose |
|---|---|---|
| `constitutional_architecture/compiler/*` (multiple) | `constitutional_architecture.isr.*` | Constitutional compiler |
| `constitutional_architecture/engine/*` | `constitutional_architecture.isr.*` | Constitutional engine |
| `constitutional_architecture/compilers/*` | `constitutional_architecture.isr.*` via `UniversalISR` | Per-category compilers |
| `constitutional_architecture/tests/test_end_to_end.py` | `constitutional_architecture.isr.*` | Constitutional tests |

**Note:** No canonical consumer (isr/core, compiler/core, reqgraph, evolution/core, certification, release) imports from `constitutional_architecture/isr/*` or `constitutional_architecture/core/models/isr.py`. (Verified in R1-C C10.)

---

## 9. Tests

### 9.1 Canonical ISR tests

| Test file | Purpose |
|---|---|
| `tests/test_isr_substrate_v12.py` | Canonical ISR substrate tests |
| `tests/v12/test_isr_gates.py` | ISR gate tests |
| `tests/v12/test_genesis_gates.py` | Genesis gate tests (uses isr.core) |
| `tests/v13/test_evolution_gates.py` | Evolution gate tests (uses isr.core) |
| `tests/v14/test_multi_backend.py` | Multi-backend tests (uses isr.core) |
| `tests/cbc1/test_cbc1_gates.py:43-45` | CBC1 gate tests (uses isr.core) |
| `tests/cbc1/test_campaign_a.py:23-25` | Campaign A tests (uses isr.core) |

### 9.2 Constitutional ISR tests

| Test file | Purpose |
|---|---|
| `constitutional_architecture/tests/test_end_to_end.py:68, 567` | Constitutional end-to-end tests (uses `constitutional_architecture.isr.*`) |
| `constitutional_architecture/tests/test_isr_to_graph.py` | Constitutional TypedGraph adapter tests (lossy round-trip) |
| `constitutional_architecture/tests/test_graph_to_isr.py` | Constitutional TypedGraph adapter tests |

**Note:** The constitutional tests are NOT in the canonical Tier A. They run only in `constitutional_architecture/tests/`, not in `tests/cbc1/`.

---

## 10. Ownership summary

| Module | Owner | Status | R1-D.1 classification |
|---|---|---|---|
| `isr/core/` | Canonical | KEEP | (canonical; no change to taxonomy) |
| `isr/ports/`, `isr/adapters/`, `isr/schema/` | Canonical | KEEP | (canonical; no change) |
| `constitutional_architecture/isr/model/isr.py:ISR` | Constitutional | LEGACY | MIGRATE_SEMANTICS (selective) + RETIRE (model) |
| `constitutional_architecture/isr/model/system.py:System` | Constitutional | LEGACY | RETIRE (rich model not canonical) |
| `constitutional_architecture/isr/semantics/requirement.py` | Constitutional | LEGACY | MIGRATE (semantic principle) |
| `constitutional_architecture/isr/semantics/testing_anchor.py` | Constitutional | LEGACY | MIGRATE (semantic principle) |
| `constitutional_architecture/isr/semantics/threat.py` | Constitutional | LEGACY | MIGRATE (semantic principle) |
| `constitutional_architecture/isr/semantics/capability.py` | Constitutional | LEGACY | MIGRATE (minimal) |
| `constitutional_architecture/isr/semantics/deployment.py` | Constitutional | LEGACY | MIGRATE (minimal) |
| `constitutional_architecture/isr/semantics/boundary.py` | Constitutional | LEGACY | ALREADY CANONICAL (EDGE_TYPE_COMPATIBILITY) |
| `constitutional_architecture/isr/semantics/projection.py` | Constitutional | LEGACY | ALREADY CANONICAL (compute_content_hash) |
| `constitutional_architecture/isr/semantics/temporal.py` | Constitutional | LEGACY | DEFER (not in flat model) |
| `constitutional_architecture/isr/semantics/migration.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/semantics/reliability.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/semantics/documentation.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/semantics/evolution_policy.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/semantics/decision.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/semantics/application_identity.py` | Constitutional | LEGACY | DEFER |
| `constitutional_architecture/isr/serialization/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-D.x) |
| `constitutional_architecture/isr/versioning/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-E.6) |
| `constitutional_architecture/isr/diff/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-D.3) |
| `constitutional_architecture/isr/metrics/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-D.3) |
| `constitutional_architecture/isr/completeness/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-D.1) |
| `constitutional_architecture/isr/graph/*`, `isr_graph.py`, `legacy_model.py` | Constitutional | LEGACY | RETIRE |
| `constitutional_architecture/isr/views/*` | Constitutional | DEFER | DEFER (out of R1 scope) |
| `constitutional_architecture/isr/profiles/*` | Constitutional | DEFER | DEFER (out of R1 scope) |
| `constitutional_architecture/isr/irr/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (R1-D.1) |
| `constitutional_architecture/isr/eir/*` | Constitutional | LEGACY | R1-D.3 (Evolution/EIR) |
| `constitutional_architecture/isr/types/*` | Constitutional | LEGACY | R1-D.x |
| `constitutional_architecture/isr/validation/*` | Constitutional | LEGACY | MIGRATE_SEMANTICS (selective; R1-D.1) |
| `constitutional_architecture/core/models/isr.py:UniversalISR` | Constitutional | LEGACY | RETIRE (R1-D.5) |

---

## 11. Cross-references

- D03: `folder/CONTRACT_CanonicalISR.md` (R1-B canonical ISR contract).
- D13: `folder/CONTRACT_CrossContractIdentity_Provenance.md` (cross-contract identity model).
- D17: `folder/CONTRACT_LegacyBoundarySpecification.md` (legacy boundary).
- R1-C C12: `folder/R1_C_GATE_REPORT.md` (R1-C gate report; PASS).
- R1-C C10: `folder/R1_C_LEGACY_BOUNDARY_REPORT.md` (2 findings: F-C10-01, F-C10-02 in `evolution/`).

---

*End of D1. The R1-D.1 ISR semantic inventory is complete. 12 constitutional validators classified (5 MIGRATE, 2 ALREADY CANONICAL, 5 DEFER). D2 (semantic comparison) follows.*
