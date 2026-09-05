# R1_D1_ISR_SEMANTIC_COMPARISON (R1-D.1 D2)

**Status:** R1-D.1 Deliverable D2. Semantic comparison between canonical ISR and constitutional ISR implementations. Index: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md` (D1), `folder/CONTRACT_CanonicalISR.md` (D03).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

**Method:** Field-by-field and validator-by-validator comparison. Each row is OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN.

---

## 1. Purpose

The R1-D.1 master prompt requires a semantic matrix comparing the canonical ISR (`isr/core/`) against the constitutional ISR implementations. The matrix identifies:

- What is present in both (retain canonical).
- What is richer in the constitutional (selective migration candidates).
- What is unique to the canonical (retain canonical).
- What is technology-specific (reject).
- What is not applicable to the flat canonical model (defer).

---

## 2. NodeType comparison

| NodeType | Canonical (`isr/core/graph.py:11-20`) | Constitutional System model | UniversalISR | Action | Reason |
|---|---|---|---|---|---|
| `DOMAIN` | ✓ ("domain") | ✗ (no direct equivalent) | ✗ | retain canonical | The canonical `DOMAIN` is the problem-domain node. The constitutional model uses `SYSTEM` and `MODULE` for a richer hierarchy. |
| `CAPABILITY` | ✓ ("capability") | ✗ (no direct equivalent; capabilities are a field on `BusinessCapability`) | ✗ | retain canonical | The canonical `CAPABILITY` is a first-class node. The constitutional model has capabilities as a field, not a node. |
| `SERVICE` | ✓ ("service") | ✓ (as `SERVICE` NodeType) | ✓ (as `SERVICE` NodeType) | retain canonical | All three have `SERVICE`. The canonical is the authoritative contract. |
| `API` | ✓ ("api") | ✓ (as `INTERFACE` NodeType) | ✓ (as `API_ENDPOINT` NodeType) | retain canonical with docstring | The canonical `API` is technology-neutral. The constitutional `INTERFACE` and `API_ENDPOINT` are equivalent. |
| `DATA_MODEL` | ✓ ("data_model") | ✓ (as `ENTITY` NodeType) | ✓ (as `DATA_ENTITY` NodeType) | retain canonical | All three have a data-model node. |
| `EVENT` | ✓ ("event") | ✓ (as `EVENT` NodeType) | ✓ (as `EVENT` NodeType) | retain canonical | All three have `EVENT`. |
| `SECURITY_POLICY` | ✓ ("security_policy") | ✓ (as `POLICY` NodeType) | ✓ (as `SECURITY_POLICY` NodeType) | retain canonical | The canonical is technology-neutral. |
| `INFRASTRUCTURE_TARGET` | ✓ ("infrastructure_target") | ✓ (as `DEPLOYMENT` NodeType) | ✓ (as `INFRA_REQUIREMENT` NodeType) | retain canonical | The canonical is technology-neutral. |
| `REQUIREMENT_REF` | ✓ ("requirement_ref") | ✗ (requirements are a field, not a node) | ✗ | retain canonical | The canonical `REQUIREMENT_REF` is a first-class node with `ref_id`. The constitutional model has requirements as a field on `System`. |
| `SYSTEM` | ✗ (no direct equivalent) | ✓ (as root container) | ✗ | **REJECT** | The constitutional `SYSTEM` is the root container of the rich model. The canonical ISR is flat; there is no `SYSTEM` node. |
| `MODULE` | ✗ | ✓ | ✗ | **REJECT** | The constitutional `MODULE` is a grouping node. The canonical ISR is flat. |
| `ENTITY` | ✗ | ✓ | ✓ (as `DATA_ENTITY`) | **REJECT** | The canonical `DATA_MODEL` subsumes this. |
| `WORKFLOW` | ✗ | ✓ | ✗ | **DEFER** | Workflows are not in the canonical flat model. |
| `POLICY` | ✗ | ✓ | ✓ (as `SECURITY_POLICY`, `TENANCY_POLICY`, `RETENTION_POLICY`, `AUDIT_POLICY`, `OPERATIONAL_POLICY`) | **DEFER** (some become `SECURITY_POLICY`) | The canonical has `SECURITY_POLICY`; the constitutional has a broader `POLICY` family. |
| `INTERFACE` | ✗ | ✓ | ✗ | **REJECT** | Subsumed by canonical `API`. |
| `DEPLOYMENT` | ✗ | ✓ | ✗ | **REJECT** | Subsumed by canonical `INFRASTRUCTURE_TARGET`. |
| `CONSTRAINT` | ✗ | ✓ | ✗ | **DEFER** | Constraints are not in the canonical flat model. |
| `FIELD` | ✗ | ✓ | ✓ (as `DATA_ATTRIBUTE`) | **REJECT** | Fields/attributes are properties of `DATA_MODEL`, not nodes. |
| `OPERATION` | ✗ | ✓ | ✗ | **REJECT** | Operations are properties of `SERVICE`, not nodes. |
| `STATE` | ✗ | ✓ | ✗ | **DEFER** | State machines are not in the canonical flat model. |
| `TRANSITION` | ✗ | ✓ | ✗ | **DEFER** | State transitions are not in the canonical flat model. |
| `RULE` | ✗ | ✓ | ✗ | **DEFER** | Rules are not in the canonical flat model. |
| `PERMISSION` | ✗ | ✓ | ✗ | **DEFER** | Permissions are properties of `SECURITY_POLICY`, not nodes. |
| `ENDPOINT` | ✗ | ✗ | ✓ (as `API_ENDPOINT`) | **REJECT** | Subsumed by canonical `API`. |
| `CONFIGURATION` | ✗ | ✓ | ✗ | **REJECT** | Configuration is a property, not a node. |
| `DOCUMENTATION` | ✗ | ✓ | ✗ | **DEFER** | Documentation is not in the canonical flat model. |
| `TEST_STRATEGY` | ✗ | ✓ | ✗ | **DEFER** | Test strategy is not in the canonical flat model. |
| `COMPONENT` | ✗ | ✗ | ✓ | **REJECT** | Subsumed by canonical `SERVICE`. |
| `FRONTEND_VIEW` | ✗ | ✗ | ✓ | **REJECT** | Frontend views are not in the canonical ISR (technology-neutral). |
| `INFRA_REQUIREMENT` | ✗ | ✗ | ✓ | **REJECT** | Subsumed by canonical `INFRASTRUCTURE_TARGET`. |
| `SLO_DEFINITION` | ✗ | ✗ | ✓ | **DEFER** | SLOs are not in the canonical flat model. |
| `TELEMETRY_REQUIREMENT` | ✗ | ✗ | ✓ | **DEFER** | Telemetry is not in the canonical flat model. |

**Summary:** 9 canonical NodeType are retained. 13 constitutional NodeType are rejected (subsumed by canonical). 8 constitutional NodeType are deferred (not in the flat model).

---

## 3. EdgeType comparison

| EdgeType | Canonical (`isr/core/graph.py:23-31`) | Constitutional System model | UniversalISR | Action | Reason |
|---|---|---|---|---|---|
| `SATISFIES` | ✓ | ✗ (as `IMPLEMENTS` for capabilities) | ✗ | retain canonical | The canonical `SATISFIES` is CAPABILITY → REQUIREMENT_REF. The constitutional `IMPLEMENTS` is different. |
| `IMPLEMENTED_BY` | ✓ | ✗ | ✗ | retain canonical | The canonical `IMPLEMENTED_BY` is CAPABILITY → SERVICE. |
| `EXPOSES` | ✓ | ✗ | ✗ | retain canonical | The canonical `EXPOSES` is SERVICE → API. |
| `PERSISTS` | ✓ | ✗ | ✗ | retain canonical | The canonical `PERSISTS` is SERVICE → DATA_MODEL. |
| `PUBLISHES` | ✓ | ✗ (as `EMITS`) | ✓ (as `EMITS`) | retain canonical | The canonical `PUBLISHES` is SERVICE → EVENT. |
| `CONSUMED_BY` | ✓ | ✗ (as `CONSUMES`) | ✓ (as `CONSUMES`) | retain canonical | The canonical `CONSUMED_BY` is EVENT → SERVICE. |
| `DEPENDS_ON` | ✓ | ✓ | ✓ | retain canonical | All three have `DEPENDS_ON`. |
| `SECURED_BY` | ✓ | ✓ (as `SECURED_BY`) | ✓ (as `SECURES`) | retain canonical | The canonical `SECURED_BY` is SERVICE/API → SECURITY_POLICY. |
| `OWNS` | ✗ | ✓ | ✓ | **REJECT** | The constitutional `OWNS` implies hierarchy; the canonical is flat. |
| `EMITS` | ✗ | ✓ | ✓ | **REJECT** | Subsumed by canonical `PUBLISHES`. |
| `CONSUMES` | ✗ | ✓ | ✓ | **REJECT** | Subsumed by canonical `CONSUMED_BY`. |
| `REFERENCES` | ✗ | ✓ | ✗ | **DEFER** | Generic references are not in the canonical flat model. |
| `IMPLEMENTS` | ✗ | ✓ | ✗ | **DEJECT** | Not a canonical edge. The canonical uses `IMPLEMENTED_BY` (CAPABILITY → SERVICE). |
| `DEPLOYS_TO` | ✗ | ✓ | ✗ | **REJECT** | Subsumed by canonical `INFRASTRUCTURE_TARGET` (a node, not an edge). |
| `ORCHESTRATES` | ✗ | ✓ | ✗ | **DEFER** | Orchestration is not in the canonical flat model. |
| `CONSTRAINS` | ✗ | ✓ | ✗ | **DEFER** | Constraints are not in the canonical flat model. |
| `CONTAINS` | ✗ | ✓ | ✗ | **REJECT** | The canonical is flat; no containment edges. |
| `TRANSITIONS_TO` | ✗ | ✓ | ✗ | **DEFER** | State transitions are not in the canonical flat model. |
| `TRIGGERS` | ✗ | ✓ | ✗ | **DEFER** | Triggers are not in the canonical flat model. |
| `VALIDATES` | ✗ | ✓ | ✗ | **DEFER** | Validation edges are not in the canonical flat model. |
| `DOCUMENTS` | ✗ | ✓ | ✗ | **DEFER** | Documentation edges are not in the canonical flat model. |
| `TESTS` | ✗ | ✓ | ✗ | **DEFER** | Test edges are not in the canonical flat model. |
| `EXPOSES` | ✗ | ✗ | ✓ | **REJECT** | Subsumed by canonical `EXPOSES`. |
| `PERSISTS` | ✗ | ✗ | ✓ | **REJECT** | Subsumed by canonical `PERSISTS`. |
| `RENDERS` | ✗ | ✗ | ✓ | **REJECT** | Technology-specific (frontend). |
| `HAS_ATTRIBUTE` | ✗ | ✗ | ✓ | **REJECT** | Attributes are properties, not edges. |
| `RELATES_TO` | ✗ | ✗ | ✓ | **DEFER** | Generic relations are not in the canonical flat model. |
| `GOVERNED_BY` | ✗ | ✗ | ✓ | **DEFER** | Governance edges are not in the canonical flat model. |
| `MONITORS` | ✗ | ✗ | ✓ | **DEFER** | Monitoring edges are not in the canonical flat model. |

**Summary:** 8 canonical EdgeType are retained. 9 constitutional EdgeType are rejected (subsumed by canonical). 10 constitutional EdgeType are deferred.

---

## 4. Identity and hashing comparison

| Aspect | Canonical | Constitutional | Alignment |
|---|---|---|---|
| Content hash | `compute_content_hash` (`isr/core/identity.py:44-66`): SHA-256 over canonical JSON with sorted keys, sorted node/edge IDs | `semantic_content_hash` (`constitutional_architecture/isr/semantics/projection.py`): projects only `system`; uses `canonical_form` + `canonicalize` | **ALIGNED.** Both use SHA-256 over canonical sorted JSON. The constitutional projects only the architectural payload; the canonical includes `schema_version`. The canonical approach is the authoritative contract. |
| Schema version | `schema_version` field on `ISRRevision` (`isr/core/revision.py:24`); format `MAJOR.MINOR` | `version` field on `ISR` (`constitutional_architecture/isr/model/isr.py:80`); integer | **DIFFERENT.** The canonical uses semantic versioning (`MAJOR.MINOR`); the constitutional uses an integer. The canonical is authoritative. |
| Provenance | `Provenance` (`isr/core/identity.py:18-41`): `parent_revision_id`, `requirement_refs`, `derivation_refs`, `created_by`, `created_at` (ISO8601) | `ISRProvenance` (`constitutional_architecture/isr/model/isr.py:56-64`): `created_at`, `created_by`, `parent_hash`, `mutation_description`, `evolution_run_id`, `generation` | **DIFFERENT.** The canonical has `requirement_refs` and `derivation_refs` (lineage); the constitutional has `mutation_description` and `evolution_run_id`. The canonical is authoritative. |
| Immutability | `frozen=True` (Pydantic) on all carriers | `@dataclass(frozen=True)` | **ALIGNED.** |
| Fail-closed construction | `ISRRevision.create()` calls `validate_invariants` then computes hash (`isr/core/revision.py:50-52`) | `ISR.validate_structure()` calls 12 semantic validators (`constitutional_architecture/isr/model/isr.py:112-144`) | **ALIGNED.** Both fail-closed at construction. |

**Summary:** Identity and hashing are **aligned in principle** (SHA-256, canonical JSON, frozen, fail-closed). The **schemas differ**: canonical uses semantic versioning + `requirement_refs`; constitutional uses integer versioning + `mutation_description`. The canonical is authoritative.

---

## 5. Invariants comparison

| Invariant | Canonical | Constitutional | Alignment |
|---|---|---|---|
| No duplicate edge IDs | `isr/core/invariants.py:57-60` | `ISR.validate_structure` checks `module.id` uniqueness (line 117) | **ALIGNED.** |
| Referential integrity | `isr/core/invariants.py:64-71` | Constitutional checks `module.id` uniqueness but does NOT explicitly check edge source/target existence (the constitutional model uses containment, not edges) | **CANONICAL IS STRICTER.** The canonical checks edge source/target existence; the constitutional checks module uniqueness. |
| Edge type compatibility | `isr/core/graph.py:61-93` + `isr/core/invariants.py:76-90` | (no edge type compatibility in the constitutional model; the constitutional uses `System` containment, not typed edges) | **CANONICAL IS STRICTER.** The constitutional model does not have typed edges with compatibility matrices. |
| Implementation leakage | `FORBIDDEN_IMPLEMENTATION_TERMS` (25 terms; `isr/core/invariants.py:16-42`) | Constitutional has no equivalent `FORBIDDEN_IMPLEMENTATION_TERMS` at the ISR level | **CANONICAL IS STRICTER.** The constitutional relies on downstream checks. |
| `REQUIREMENT_REF` carries `ref_id` | `isr/core/invariants.py:98-105` | (no equivalent; the constitutional has `System.requirements` as a field, not a `REQUIREMENT_REF` node) | **CANONICAL IS STRICTER.** |
| Requirement is a semantic obligation | (not yet enforced) | `validate_system_requirement_constraints` (`constitutional_architecture/isr/semantics/requirement.py`) | **MIGRATE.** The semantic principle applies to the canonical `REQUIREMENT_REF` node. |
| Testing anchor is semantic | (not yet enforced) | `validate_system_testing_anchor_constraints` (`constitutional_architecture/isr/semantics/testing_anchor.py`) | **MIGRATE.** The semantic principle applies. |
| Security threat is an obligation | (not yet enforced; canonical has `SECURED_BY` edge) | `validate_system_threat_constraints` (`constitutional_architecture/isr/semantics/threat.py`) | **MIGRATE.** The semantic principle applies. |
| Architectural boundary | `EDGE_TYPE_COMPATIBILITY` matrix | `validate_system_boundary_constraints` (`constitutional_architecture/isr/semantics/boundary.py`) | **ALREADY CANONICAL.** The canonical `EDGE_TYPE_COMPATIBILITY` IS the architectural boundary. |
| Capability constraints | (not yet enforced) | `validate_system_capability_constraints` (`constitutional_architecture/isr/semantics/capability.py`) | **MIGRATE (minimal).** |
| Deployment constraints | (not yet enforced) | `validate_system_deployment_constraints` (`constitutional_architecture/isr/semantics/deployment.py`) | **MIGRATE (minimal).** |
| Temporal constraints | (not yet enforced) | `validate_module_temporal_constraints` | **DEFER.** Temporal is not in the flat model. |
| Migration constraints | (not yet enforced) | `validate_module_migration_constraints` | **DEFER.** |
| Reliability constraints | (not yet enforced) | `validate_system_reliability_constraints` | **DEFER.** |
| Documentation constraints | (not yet enforced) | `validate_system_documentation_constraints` | **DEFER.** |
| Evolution policy constraints | (not yet enforced) | `validate_system_evolution_policy_constraints` | **DEFER.** |
| Decision constraints | (not yet enforced) | `validate_system_decision_constraints` | **DEFER.** |
| Application identity | (not yet enforced) | `constitutional_architecture/isr/semantics/application_identity.py` | **DEFER.** |

**Summary:** The canonical ISR is **stricter** on structural invariants (edge type compatibility, referential integrity, implementation leakage, `REQUIREMENT_REF.ref_id`). The constitutional ISR has **richer semantic validators** (requirement, testing_anchor, threat, capability, deployment) that are **migratable** to the canonical model. 7 constitutional validators are **deferred** (not in the flat model).

---

## 6. Semantic principle migration candidates

The genuinely-semantic principles that can be migrated to the canonical flat model:

### 6.1 Requirement is a semantic obligation (not a test mechanism)

**Constitutional source:** `constitutional_architecture/isr/semantics/requirement.py`
**Canonical target:** `isr/core/invariants.py` + `REQUIREMENT_REF` NodeType
**Migration:** Add a forbidden-term check for test mechanisms (e.g., `pytest`, `playwright`, `selenium`) on `REQUIREMENT_REF` node properties. The canonical `ref_id` is already validated; the migration adds the "requirement is not a test mechanism" check.

### 6.2 Testing anchor is semantic (not test-mechanism-specific)

**Constitutional source:** `constitutional_architecture/isr/semantics/testing_anchor.py` (line 24: `TESTING_MECHANISM_TERMS`)
**Canonical target:** `isr/core/invariants.py`
**Migration:** Add a shared `TESTING_MECHANISM_TERMS` list (or extend `FORBIDDEN_IMPLEMENTATION_TERMS`). The semantic principle: testing anchors are obligations, not test files.

### 6.3 Security threat is an obligation (security-by-design)

**Constitutional source:** `constitutional_architecture/isr/semantics/threat.py`
**Canonical target:** `SECURITY_POLICY` NodeType + `SECURED_BY` EdgeType
**Migration:** Document the security-by-design principle on `SECURITY_POLICY` and `SECURED_BY`. No code change to the taxonomy; the semantic is already enforced by the edge type compatibility.

### 6.4 Capability constraints (minimal)

**Constitutional source:** `constitutional_architecture/isr/semantics/capability.py`
**Canonical target:** `CAPABILITY` NodeType
**Migration:** Add a minimal invariant that `CAPABILITY` nodes have a non-empty name (the canonical already requires `id: str = Field(min_length=1)`; the migration adds the name check).

### 6.5 Deployment intent (minimal)

**Constitutional source:** `constitutional_architecture/isr/semantics/deployment.py`
**Canonical target:** `INFRASTRUCTURE_TARGET` NodeType
**Migration:** Document the deployment-intent semantic on `INFRASTRUCTURE_TARGET`. The canonical's `FORBIDDEN_IMPLEMENTATION_TERMS` already prevents technology-specific names.

### 6.6 Architectural boundary (ALREADY CANONICAL)

**Constitutional source:** `constitutional_architecture/isr/semantics/boundary.py`
**Canonical target:** `EDGE_TYPE_COMPATIBILITY` matrix (`isr/core/graph.py:61-93`)
**Migration:** None needed. The canonical IS the boundary.

### 6.7 Semantic content hash (ALREADY CANONICAL)

**Constitutional source:** `constitutional_architecture/isr/semantics/projection.py`
**Canonical target:** `compute_content_hash` (`isr/core/identity.py:44-66`)
**Migration:** None needed. The canonical approach is the authoritative contract.

---

## 7. Field classification

| Field class | Canonical | Constitutional | Action |
|---|---|---|---|
| `business_capabilities` | ✗ (not a field) | ✓ (on `System`) | **REJECT** — not in flat model |
| `requirements` | ✗ (not a field; `REQUIREMENT_REF` nodes) | ✓ (on `System`) | **MIGRATE** — the semantic principle (requirement is an obligation) is captured by `REQUIREMENT_REF` |
| `acceptance_criteria` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `deployment_intents` | ✗ | ✓ (on `System`) | **MIGRATE (minimal)** — captured by `INFRASTRUCTURE_TARGET` |
| `testing_anchors` | ✗ | ✓ (on `System`) | **MIGRATE** — captured by `REQUIREMENT_REF` + forbidden-term check |
| `documentation_intents` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `evolution_objectives` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `protected_regions` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `evolution_policies` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `architectural_decisions` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `security_threats` | ✗ | ✓ (on `System`) | **MIGRATE** — captured by `SECURITY_POLICY` + `SECURED_BY` |
| `reliability_requirements` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `architectural_boundaries` | ✗ (captured by `EDGE_TYPE_COMPATIBILITY`) | ✓ (on `System`) | **ALREADY CANONICAL** |
| `constraints` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `modules` | ✗ (flat model) | ✓ (on `System`) | **REJECT** — flat model |
| `deployment` | ✗ (captured by `INFRASTRUCTURE_TARGET`) | ✓ (on `System`) | **ALREADY CANONICAL** |
| `metadata` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |
| `global_policies` | ✗ | ✓ (on `System`) | **DEFER** — not in flat model |

**Summary:** 4 fields are MIGRATE (requirements, deployment_intents, testing_anchors, security_threats). 2 are ALREADY CANONICAL (architectural_boundaries, deployment). 9 are DEFER. 3 are REJECT (modules, business_capabilities, metadata-related).

---

## 8. Compatibility requirements

The canonical ISR is **forward-compatible** with a future Compiler IR:

- The canonical ISR's `schema_version` (semantic versioning) allows the ISR contract to evolve without breaking the Compiler IR.
- The canonical ISR's content hash is deterministic; the Compiler IR can reference ISR revisions by content hash.
- The canonical ISR's `REQUIREMENT_REF` nodes carry `ref_id`; the Compiler IR can trace back to requirements.

The canonical ISR is **not forward-compatible** with:

- The rich System/Module/Entity hierarchy (the constitutional model). If the Compiler IR is designed to consume the rich model, the canonical ISR cannot satisfy it without migration.
- The constitutional semantics validators (requirement, threat, etc.) that operate on the rich model. The canonical ISR has the semantic principles (via docstrings + minimal invariants) but not the full validator implementations.

**Compatibility verdict:** The canonical ISR is **forward-compatible with a future Compiler IR** that consumes the flat 9-node/8-edge model. It is **not forward-compatible** with a Compiler IR that requires the rich System model.

---

## 9. Cross-references

- D1: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md`
- D3: `folder/R1_D1_ISR_MIGRATION_MAP.md` (next deliverable)
- D03: `folder/CONTRACT_CanonicalISR.md`

---

*End of D2. The R1-D.1 semantic comparison is complete. 5 semantic principles are migration candidates; 2 are already canonical; 7 are deferred. D3 (migration map) follows.*
