# ESAP RequirementGraph Consumer Inventory — FS-00 Remediation A1

**Document ID:** ESAP-RM-A1-001  
**Status:** SOURCE-INVENTORY COMPLETE FOR IDENTIFIED MODELS; ROUTE-REACHABILITY REVIEW OPEN  
**Audited branch base:** `15d28b79726bd020e8d39dbbb98dd97f5d56d09e`  
**Remediation branch:** `remediation/fs00-authority-reconciliation`  
**Related baseline:** [ESAP Authority Reconciliation](ESAP_AUTHORITY_RECONCILIATION_V1.md)

## 1. Executive result

The repository contains at least **five materially different requirement-graph/requirement-IR representations**, not one RequirementGraph model with harmless aliases. Their node taxonomies, edge semantics, validation behavior, mutability, provenance and downstream outputs differ.

The canonical target remains `reqgraph/core` under D02. The other models cannot be treated as interchangeable and cannot be declared retired merely by documenting a canonical owner: several still have executable consumers. This inventory is a source-level inventory of identified models and direct consumers; it does not claim every API/runtime route has been dynamically exercised.

**No graph model was deleted, renamed, or migrated.** This is an inventory and migration-planning artifact only.

## 2. Model inventory

| ID | Model / source | Shape and semantics | Validation / identity | Current disposition |
|---|---|---|---|---|
| RG-01 | `reqgraph/core/graph.py:RequirementGraph` | Pydantic frozen graph; requirements and typed relationships; D02's four edge kinds `DEPENDS_ON`, `CONFLICTS_WITH`, `REFINES`, `OWNED_BY`. Requirement kinds include functional, non-functional, domain concept, stakeholder and constraint. | Immutable model; canonical package has explicit validation and content-addressed adapter helpers. | **TARGET CANONICAL AUTHORITY.** Preserve and extend only through ADR/versioning. |
| RG-02 | `tiannara/domain/models/requirement_graph.py:RequirementGraph` | Pydantic graph with list-based nodes/edges, graph provenance and derived analysis; richer requirement kinds, verification method and edges including `REALIZES`, `CONSTRAINS`, `DERIVES_FROM`. | Structural checks reject duplicate IDs/dangling/duplicate edges; semantic findings are attached as analysis and do not uniformly block construction. Graph has its own content hash. | **ACTIVE LEGACY / ADAPTER CANDIDATE.** Used by the IntentCompiler and constitutional source-binding/projection paths; not retired. |
| RG-03 | `autonomous-api/app/engine/requirement_ir.py:RequirementGraph` | Mutable dataclass of `requirements: dict` and `issues`; requirement values carry acceptance criteria, dependencies, conflicts, tags and source. | Validation returns issue records; mutable graph/issue collections; a separate deterministic topological ordering and CAP-001 EngineeringISR projection. | **ACTIVE PARALLEL CAP-001 MODEL.** Used by requirement analysis, architecture-obligation and evidence/certification modules; not equivalent to RG-01. |
| RG-04 | `constitutional_architecture/core/models/requirements_graph.py:RequirementsGraph` | Mutable domain/architecture graph of capabilities, personas, data domains, quality attributes, compliance standards, operational constraints, business goals and architecture objectives. | In-memory mutable graph with its own nodes, edges, validation, dependency and impact operations. It is not the D02 requirement graph carrier. | **LEGACY / ARCHITECTURE-PLANNING GRAPH.** Consumed by two ProductTopologyResolver implementations; disposition requires route/consumer analysis. |
| RG-05 | `constitutional_architecture/isr/irr/graph.py:RequirementGraph` plus `constitutional_architecture/irr/schema.py:IRR` | Frozen dataclass graph built from IRR requirements and domain concepts; relationship is an untyped string; builder emits `relates_to` for related requirements. | No content-addressed identity or complete validation contract shown in this builder. | **LEGACY / REACHABILITY UNKNOWN.** Definition and builder exist; direct production consumers were not established in the searched code. |

### 2.1 Related but distinct CAP-001 projection

`autonomous-api/app/engine/requirement_isr.py` projects RG-03 into `EngineeringISR`, not `isr.core.revision.ISRRevision`. It creates entities from explicit tags, policies from selected requirement kinds, invariants using lexical token checks, and interfaces using lexical keyword checks. Its traceability can show that a source requirement ID appears in the projection; it does not establish that the full requirement meaning or all typed behavioral obligations were represented.

This is a distinct projection contract and must not be presented as the canonical ISR implementation.

## 3. Identified direct consumers and execution paths

| Model | Direct consumers / builders inspected | Evidence classification | Important boundary |
|---|---|---|---|
| RG-01 `reqgraph/core` | `reqgraph/ingestion/tor_extractor.py`; `reqgraph/adapters/tor_isr.py`; `reqgraph/adapters/isr_projection.py`; `genesis/mapper.py`; `certification/campaign/plan_builder.py`; `certification/payroll/readiness.py`; `certification/payroll/certifier.py`; `certification/authorization/verifier.py`. | Source-bound TOR/Genesis and Campaign A paths are present in source; these are distinct from proof that every product route uses them. | The strongest current requirement → ISRRevision → CompilationPlan lineage uses this model. |
| RG-02 `tiannara/domain/models/requirement_graph.py` | `tiannara/application/intent/graph_builder.py`; `tiannara/application/intent/compiler.py`; `tiannara/application/intent/synthesis.py`; `constitutional_architecture/compiler/source_binding.py`; `constitutional_architecture/isr/semantics/intent_projection.py`; TaskFlow provider-free adapter/gate. | IntentCompiler and CLI composition are source-wired; source-binding and projection functions are explicit. Production HTTP/API reachability and full end-to-end enforcement are not established by this inventory. | It carries fields/edge kinds not represented in RG-01. No implicit cast or lossy conversion is permitted. |
| RG-03 CAP-001 `requirement_ir.py` | `requirement_analyzer.py`; `requirement_isr.py`; `requirement_certification.py`; `requirement_architecture_bridge.py`; `quality_requirements.py`; `requirement_implementation_verification_chain.py`; `requirement_evidence_certification.py`. | In-process function chain and unit-test modules are present. Whether this chain is a production API route and whether its certification state is authoritative for the main compiler are UNKNOWN. | Its EngineeringISR is not the canonical ISRRevision; it must not certify mainline compiler behavior by itself. |
| RG-04 `RequirementsGraph` | `constitutional_architecture/core/pipeline/topology_resolver.py`; `constitutional_architecture/engine/bridges/topology_bridge.py`. | Two executable resolver implementations construct/consume the architecture graph. Route selection between them was not established. | Architecture-planning graph, not interchangeable with requirements traceability graph. |
| RG-05 IRR graph | `RequirementGraphBuilder.from_irr` in `constitutional_architecture/isr/irr/graph.py`; IRR imports in constitutional tests. | Definition and builder are present; no direct call site for `from_irr` surfaced in the targeted code search. | Do not label retired until a broader call/import and dynamic reachability search is complete. |


### 3.1 Entry-point and route reachability checks

Additional call-site searches and composition-root inspection refine the table above:

- **RG-02 IntentCompiler:** `tiannara/application/compiler/composition.py` constructs the typed `IntentCompiler` and connects it to the Cap-C ProjectCompiler registry. The module documents CLI embedding (`tiannara create ...`) and tests exercise the composition. This establishes a real application/CLI composition path, but does not establish that all Tiannara or Autonomous API routes use it. The separate `tiannara/bootstrap.py` calibration harness uses `StructuredIntentCompiler`, a deterministic legacy ISR stub, rather than this RequirementGraph-producing IntentCompiler. These are distinct paths.
- **RG-03 CAP-001:** targeted repository code searches found the analyzer, CAP-001 EngineeringISR projector, certification and requirement-chain functions in their implementation modules and tests, but did not find a production API/router import or call site for `decompose_statements` or `certify_requirements`. Their production route reachability is therefore **NOT ESTABLISHED**; do not treat CAP-001 certification output as the main compiler's authoritative certification.
- **RG-04 architecture graph:** both `constitutional_architecture/core/pipeline/topology_resolver.py` and `constitutional_architecture/engine/bridges/topology_bridge.py` define a `ProductTopologyResolver` and build the mutable `RequirementsGraph`. Their existence and callers in tests are established; which resolver is the active production route and whether both remain reachable require further bootstrap/API call-graph tracing.
- **RG-05 IRR graph:** `RequirementGraphBuilder.from_irr` is defined, but the targeted call-site search did not find a direct invocation. Treat it as dormant/unknown, not proven retired.
- **RG-01 canonical campaign:** `certification/campaign/plan_builder.py` is the strongest complete source-to-plan route found in this inventory. It uses canonical `reqgraph/core`, `genesis/mapper.py`, `isr/core/ISRRevision` and `compiler/core/isr_to_plan`. It remains a campaign/reference route, not proof that the broader production API uses the same chain.

Searches were repository code-search queries plus direct inspection of the identified files at the remediation branch base. Search indexing and dynamic imports can omit call sites; this is why the remaining classifications stay UNKNOWN rather than being upgraded to unreachable or retired.

## 4. Semantic incompatibilities that block a naive adapter

1. **Different edge vocabularies:** RG-01's four edges do not directly encode RG-02's `REALIZES`, `CONSTRAINS` and `DERIVES_FROM`, RG-03's requirement fields, or RG-05's generic `relates_to`.
2. **No equivalence by label:** mapping `REALIZES` to ISR `SATISFIES` is a semantic claim. It requires a defined direction, subject/object type, evidence standard and acceptance rule; it must not be inferred from similar words.
3. **Different priority and kind taxonomies:** CAP-001 includes security, operational and compliance kinds; RG-02 includes integration, data, business rule, assumption and unclassified; RG-01 has a smaller fixed taxonomy. Unknown values cannot be coerced to functional or constraint.
4. **Different validation semantics:** RG-02 separates structural validation from nonblocking analysis findings; RG-03 returns issues on a mutable graph; RG-01 is intended to fail closed at the canonical boundary. A conversion cannot upgrade warnings or unresolved issues to approved requirements.
5. **Different provenance and identity:** RG-01 graph identity, RG-02 source statement hash / graph hash, RG-03 source string and CAP-001 traceability, and RG-05 IRR identity are not interchangeable. A target hash must be newly computed over the mapped canonical content and remain bound to the source identity.
6. **Different lifecycle guarantees:** RG-01 is frozen; RG-02 and RG-03 expose mutable collections; RG-04 is explicitly mutable. An adapter must snapshot, validate and freeze its output; it must not imply the source was immutable.
7. **Requirement reference is not realization:** the canonical `reqgraph/adapters/isr_projection.py` intentionally emits requirement-reference nodes and relationship edges only. It does not establish `SATISFIES` or prove implementation.

## 5. Required migration disposition

| Source | Proposed disposition | Conditions before changing consumers |
|---|---|---|
| RG-01 | KEEP as sole canonical RequirementGraph | D02 contract reconciliation and schema tests remain required. |
| RG-02 | MIGRATE through a versioned adapter; retain read compatibility during migration | Define every field/edge mapping; block unknown/lossy semantics; preserve source hash, approval and reviewer provenance; migrate IntentCompiler and source-binding paths only after parity tests. |
| RG-03 | MIGRATE CAP-001 obligations into canonical RequirementGraph + canonical ISRRevision, or explicitly isolate CAP-001 as a separate non-authoritative analysis product | Map all requirement kinds, priorities, acceptance criteria, dependencies/conflicts and evidence references; replace EngineeringISR as mainline ISR authority; prove route boundary before retirement. |
| RG-04 | KEEP as a distinct ArchitecturePlanningGraph only if its consumers still require it; rename/document to avoid RequirementGraph authority collision | Verify resolver entrypoints and callers; ensure its output is an ArchitectureCandidate/plan input referencing canonical ISR rather than a competing requirement authority. |
| RG-05 | DEFER / retire only after reachability proof | Complete import/call graph, tests and runtime route search; preserve IRR source migration if still used. |

These are target dispositions, not authorization to delete or rewrite source models in A1.

## 6. A1 acceptance status

| Acceptance item | Status |
|---|---|
| Identify canonical RequirementGraph package | PASS — RG-01 / D02 |
| Identify parallel graph model definitions | PASS — RG-02 through RG-05 identified |
| Identify direct consumers of canonical graph | PASS — TOR/Genesis/Campaign A paths |
| Identify direct consumers of noncanonical graphs | PARTIAL — source consumers listed; route reachability incomplete |
| Establish exact production route reachability for every consumer | UNKNOWN |
| Define semantic adapter rules and loss handling | SPECIFIED in Section 4; executable adapter not implemented |
| Prove no silent loss across migration | NOT RUN / NOT ESTABLISHED |
| Retire competing RequirementGraph runtime consumers | NOT AUTHORIZED / NOT STARTED |

**A1 result: SOURCE INVENTORY COMPLETE FOR IDENTIFIED MODELS; PARTIAL ROUTE REACHABILITY ESTABLISHED; MIGRATION BLOCKED PENDING FULL CALL-GRAPH AND SEMANTIC MAPPING.**

## 7. Next remediation actions

1. Trace the IntentCompiler and CAP-001 paths from actual CLI/API/job entrypoints to determine production reachability and publication effects.
2. Complete import/call graph analysis for RG-04 and RG-05, including dynamically loaded modules and tests.
3. Produce field/edge mapping tables for RG-02 and RG-03 against RG-01. Any nonrepresentable required field/edge remains a blocker.
4. Add adapter contract tests only after the mapping has been reviewed; do not implement an adapter that guesses at semantics.
5. Update D02 and the canonical contract registry only when the migration design is approved and supported by executable evidence.

**Change boundary:** documentation-only. No runtime behavior, model schema, compiler route, backend, certification or production capability was changed.
