# R1_D1_ISR_LEGACY_DISPOSITION (R1-D.1 D6)

**Status:** R1-D.1 Deliverable D6. ISR legacy disposition. Index: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md` (D1), `folder/R1_D1_ISR_MIGRATION_MAP.md` (D4).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

---

## 1. Purpose

Explicitly classify every constitutional ISR implementation per the R1-D.1 master prompt's taxonomy: KEEP / MIGRATE / REPLACE / RETIRE / DEFER. No unexplained duplicate ISR remains.

---

## 2. Disposition table

| Item | Source | Disposition | Reason | Migration step |
|---|---|---|---|---|
| `constitutional_architecture/isr/model/isr.py:ISR` | Constitutional ISR root | **RETIRE** | The canonical ISR is `isr/core/`. The constitutional ISR root is not the canonical ISR. Its semantic validators are selectively absorbed (M-01–M-05 → 3 MIGRATE, 2 DEFERRED). The rich model is retired as runtime. | R1-D.5 |
| `constitutional_architecture/isr/model/system.py:System` | Constitutional System model | **RETIRE** | The rich System model (modules, deployment, business_capabilities, requirements, etc.) is not in the canonical flat 9-node/8-edge model. Retired. | R1-D.5 |
| `constitutional_architecture/isr/model/{module,entity,service,workflow,policy,interface,event,deployment,constraints,edges,fields,nodes}.py` | Constitutional model components | **RETIRE** | All retired as part of the System model retirement. | R1-D.5 |
| `constitutional_architecture/core/models/isr.py:UniversalISR` | Third ISR model | **RETIRE** | No canonical consumer. Retired. | R1-D.5 |
| `constitutional_architecture/isr/semantics/requirement.py` | Constitutional semantic validator | **MIGRATE** (M-01) | The semantic principle (requirement is a semantic obligation, not a test mechanism) is absorbed into `isr/core/invariants.py` as `TESTING_MECHANISM_TERMS`. | **DONE (R1-D.1)** |
| `constitutional_architecture/isr/semantics/testing_anchor.py` | Constitutional semantic validator | **MIGRATE** (M-02) | The `TESTING_MECHANISM_TERMS` list is shared with M-01. Applied to all node properties. | **DONE (R1-D.1)** |
| `constitutional_architecture/isr/semantics/threat.py` | Constitutional semantic validator | **MIGRATE** (M-03) | The security-by-design principle is documented on `SECURITY_POLICY` and `SECURED_BY`. | **DONE (R1-D.1)** |
| `constitutional_architecture/isr/semantics/boundary.py` | Constitutional semantic validator | **MIGRATE → ALREADY CANONICAL** (AC-01) | The canonical `EDGE_TYPE_COMPATIBILITY` IS the architectural boundary. No migration needed. | **DONE (no-op)** |
| `constitutional_architecture/isr/semantics/projection.py` | Constitutional semantic validator | **MIGRATE → ALREADY CANONICAL** (AC-02) | The canonical `compute_content_hash` IS the semantic content hash. No migration needed. | **DONE (no-op)** |
| `constitutional_architecture/isr/semantics/capability.py` | Constitutional semantic validator | **DEFER** (was M-04) | Adding `CAPABILITY.name` requirement was a breaking change. Deferred to a future R-phase. | Future R-phase |
| `constitutional_architecture/isr/semantics/deployment.py` | Constitutional semantic validator | **DEFER** (was M-05) | Adding `INFRASTRUCTURE_TARGET.target` requirement was a breaking change. Deferred. | Future R-phase |
| `constitutional_architecture/isr/semantics/temporal.py` | Constitutional semantic validator | **DEFER** | Temporal constraints are not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/migration.py` | Constitutional semantic validator | **DEFER** | Module migration is not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/reliability.py` | Constitutional semantic validator | **DEFER** | Reliability requirements are not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/documentation.py` | Constitutional semantic validator | **DEFER** | Documentation intent is not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/evolution_policy.py` | Constitutional semantic validator | **DEFER** | Evolution policy is not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/decision.py` | Constitutional semantic validator | **DEFER** | Architectural decisions are not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/semantics/application_identity.py` | Constitutional semantic validator | **DEFER** | Application identity is not in the canonical flat model. | Future R-phase |
| `constitutional_architecture/isr/serialization/*` | Constitutional serialization | **DEFER** | R1-D.x scope (not R1-D.1). | R1-D.x |
| `constitutional_architecture/isr/versioning/*` | Constitutional versioning | **DEFER** | R1-E.6 (durable lineage). | R1-E.6 |
| `constitutional_architecture/isr/diff/*` | Constitutional diff | **DEFER** | R1-D.3 (Evolution/EIR migration). | R1-D.3 |
| `constitutional_architecture/isr/metrics/*` | Constitutional metrics | **DEFER** | R1-D.3. | R1-D.3 |
| `constitutional_architecture/isr/completeness/*` | Constitutional completeness | **DEFER** | R1-D.x. | R1-D.x |
| `constitutional_architecture/isr/graph/*`, `isr_graph.py`, `legacy_model.py` | Constitutional graph | **RETIRE** | Replaced by canonical `isr/core/graph.py`. | R1-D.5 |
| `constitutional_architecture/isr/views/*` | Constitutional views | **DEFER** | Out of R1 scope. | R2/R3 |
| `constitutional_architecture/isr/profiles/*` | Constitutional profiles | **DEFER** | Out of R1 scope. | R2/R3 |
| `constitutional_architecture/isr/irr/*` | Constitutional IRR | **DEFER** | R1-D.1 IRR migration is out of R1-D.1 scope (D02 RequirementGraph is canonical). | R1-D.x |
| `constitutional_architecture/isr/eir/*` | Constitutional EIR | **DEFER** | R1-D.3 (Evolution/EIR migration). | R1-D.3 |
| `constitutional_architecture/isr/types/*` | Constitutional types | **DEFER** | R1-D.x. | R1-D.x |
| `constitutional_architecture/isr/validation/*` | Constitutional validation | **DEFER** | R1-D.x. | R1-D.x |

---

## 3. Summary

| Disposition | Count |
|---|---|
| KEEP (canonical) | 0 (all canonical is `isr/core/`) |
| MIGRATE (done in R1-D.1) | 3 (M-01, M-02, M-03) |
| MIGRATE → ALREADY CANONICAL | 2 (AC-01, AC-02) |
| RETIRE (R1-D.5) | 5 (ISR root, System, model components, UniversalISR, constitutional graph) |
| DEFER (future R-phase) | 14 (7 semantic validators + 7 supporting infrastructure) |

---

## 4. No unexplained duplicate ISR

After R1-D.1:

- The canonical ISR is `isr/core/` (9 NodeType, 8 EdgeType, frozen Pydantic, SHA-256, TESTING_MECHANISM_TERMS added, security-by-design documented).
- No new ISR types introduced.
- No constitutional types promoted to canonical.
- The constitutional ISR implementations are explicitly classified: 3 MIGRATE (done), 2 ALREADY CANONICAL, 5 RETIRE (R1-D.5), 14 DEFER.

There is **no unexplained duplicate ISR**. The constitutional ISR is on a clear retirement path (R1-D.5) with explicit ownership and destination.

---

## 5. Cross-references

- D1: `folder/R1_D1_ISR_SEMANTIC_INVENTORY.md`
- D4: `folder/R1_D1_ISR_MIGRATION_MAP.md`
- D5: `folder/R1_D1_ISR_CONSUMER_MIGRATION.md`
- D7: `folder/R1_D1_CANONICAL_INTEGRATION_REPORT.md` (next)

---

*End of D6. The R1-D.1 ISR legacy disposition is complete. 3 MIGRATE (done), 2 ALREADY CANONICAL, 5 RETIRE (R1-D.5), 14 DEFER. No unexplained duplicate ISR.*
