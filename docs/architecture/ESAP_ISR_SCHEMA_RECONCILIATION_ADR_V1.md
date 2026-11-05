# ISR Schema Reconciliation ADR — FS-00 Remediation A2

**ADR ID:** ESAP-ADR-FS00-002  
**Status:** APPROVED BY USER — IMPLEMENTATION IN PROGRESS  
**Target owner:** `isr/core`  
**Related contracts:** D03 `folder/CONTRACT_CanonicalISR.md`; schema registry `isr/schema/versions.py`; authority baseline `docs/architecture/ESAP_AUTHORITY_RECONCILIATION_V1.md`  
**Parent audit:** FS-00 Checkpoint 15  
**Change boundary:** design only; no schema, runtime, fixtures, hashes, or certifications are modified.

---

## 1. Decision required

D03 freezes the canonical ISR at 9 node kinds and 8 edge kinds. The inspected implementation in `isr/core/graph.py` contains 14 node kinds and 18 edge kinds. The schema registry declares `CURRENT_SCHEMA_VERSION = "1.1"`, but its only migration (`1.0 → 1.1`) adds a `schema_version` property to nodes; it does not register or validate node/edge taxonomies. `ISRRevision.create` validates graph invariants and behavioral payloads but accepts any syntactically valid MAJOR.MINOR version.

The taxonomy expansion is not merely documentation drift: it adds first-class frontend, effect, invariant, consequence and requirement-relationship semantics, and the compiler lowering consumes those kinds.

**Proposed decision:** retain all current 14 node kinds and 18 edge kinds as the intended canonical ISR semantic surface, and introduce an explicitly versioned schema contract that represents this expanded vocabulary. Do not delete or flatten the added semantic types to restore the old 9/8 count.

**Version recommendation:** introduce schema **2.0** for the expanded 14/18 contract because the existing D03 1.x contract explicitly freezes a smaller taxonomy and older readers may reject unknown enum values. This is a proposal for governance review, not an already approved version transition.

## 2. Exact proposed schema 2.0 taxonomy

### 2.1 Node kinds (14)

| Kind | Semantic role |
|---|---|
| `DOMAIN` | Problem domain / bounded context |
| `CAPABILITY` | Technology-neutral system capability |
| `SERVICE` | Logical service boundary |
| `API` | Technology-neutral API operation/surface |
| `DATA_MODEL` | Domain data model |
| `EVENT` | Domain event |
| `SECURITY_POLICY` | Authorization/security obligation |
| `INFRASTRUCTURE_TARGET` | Technology-neutral infrastructure intent |
| `REQUIREMENT_REF` | Reference to a source requirement |
| `FRONTEND_ROUTE` | User-facing route/view boundary |
| `FRONTEND_INTERACTION` | User interaction/action obligation |
| `EFFECT` | Declared externally observable side effect |
| `INVARIANT` | State or behavior property that must hold |
| `CONSEQUENCE` | Observable outcome linked to an effect or invariant |

### 2.2 Edge kinds (18)

| Kind | Source → target | Semantic role |
|---|---|---|
| `SATISFIES` | CAPABILITY → REQUIREMENT_REF | Explicit realization claim; requires evidence policy |
| `IMPLEMENTED_BY` | CAPABILITY → SERVICE | Capability implementation allocation |
| `EXPOSES` | SERVICE → API | Service/API ownership |
| `PERSISTS` | SERVICE → DATA_MODEL | Persistence responsibility |
| `PUBLISHES` | SERVICE → EVENT | Event publication |
| `CONSUMED_BY` | EVENT → SERVICE | Event consumption |
| `DEPENDS_ON` | SERVICE/CAPABILITY → SERVICE/CAPABILITY | Explicit dependency |
| `SECURED_BY` | SERVICE/API → SECURITY_POLICY | Security obligation binding |
| `CONTAINS` | DOMAIN/SERVICE/FRONTEND_ROUTE → owned component | Containment / ownership |
| `ROUTES_TO` | FRONTEND_ROUTE → API | Route-to-API binding |
| `INVOKES` | FRONTEND_INTERACTION → API/SERVICE | Interaction invocation binding |
| `CAUSES_EFFECT` | API/SERVICE/EVENT → EFFECT | Source-bound effect binding |
| `REQUIRES_INVARIANT` | DATA_MODEL/SERVICE/EFFECT → INVARIANT | Invariant obligation binding |
| `CONSEQUENCE_OF` | CONSEQUENCE → EFFECT/INVARIANT | Observable outcome binding |
| `REQUIREMENT_DEPENDS_ON` | REQUIREMENT_REF → REQUIREMENT_REF | Preserved source dependency |
| `REQUIREMENT_CONFLICTS_WITH` | REQUIREMENT_REF → REQUIREMENT_REF | Preserved source conflict |
| `REQUIREMENT_REFINES` | REQUIREMENT_REF → REQUIREMENT_REF | Preserved source refinement |
| `REQUIREMENT_OWNED_BY` | REQUIREMENT_REF → REQUIREMENT_REF | Preserved source ownership |

The table mirrors the current `NodeType`, `EdgeType` and `EDGE_TYPE_COMPATIBILITY` definitions. Before implementation, the exact source/target matrix must be copied from code into a schema fixture and compared mechanically so documentation cannot drift again.

## 3. Additional implementation findings to resolve

### 3.1 Version registry does not enforce schema versions

Observed:
- `isr/schema/versions.py` and `isr/schema/__init__.py` contain duplicate registry/migration definitions.
- `CURRENT_SCHEMA_VERSION` is `1.1`; `LATEST_MIGRATION` is `("1.0", "1.1")`.
- `migrate_1_0_to_1_1` adds `schema_version: "1.1"` to every node and leaves edges unchanged.
- `ISRRevision.create` validates only the MAJOR.MINOR string format before accepting the graph. It does not reject unsupported schema versions or validate the graph against a registered schema-specific taxonomy.
- The TOR adapter and campaign plan builder construct revisions with `schema_version="1.0"` while the current graph implementation includes the expanded semantic vocabulary.

Required remediation:
1. establish one schema registry module and make package exports re-export it rather than duplicate it;
2. validate supported versions in `ISRRevision.create`;
3. dispatch node/edge taxonomy, payload and compatibility validation by schema version;
4. reject unknown schema versions and unknown node/edge kinds before hashing;
5. ensure migration functions are deterministic, pure, version-directed and covered by round-trip tests.

### 3.2 Content hash does not include provenance

D03 says the provenance hash is included in ISR content identity. The inspected `compute_content_hash(schema_version, graph)` hashes schema version, sorted nodes and sorted edges; it does not accept or include `Provenance`. Therefore two revisions with identical graph/schema but different provenance can receive the same content hash.

This is a contract/implementation discrepancy and requires an explicit decision:
- **Option A (recommended for revision identity):** keep graph semantic hash independent of provenance, but introduce a separate immutable revision-envelope hash that binds graph hash, schema version, provenance hash, parent revision and migration identity. Rename/document the current hash as graph semantic content hash and update D03 accordingly; or
- **Option B:** change the content hash to include provenance, which means timestamp/author/derivation changes alter the content identity and every consumer must use the new versioned hash contract.

Option A more cleanly separates semantic equivalence from revision lineage, but it requires D03 terminology and evidence-envelope contracts to be reconciled. No hash algorithm is changed by this ADR proposal.

### 3.3 Node-level schema_version metadata

The 1.0→1.1 migration injects a schema version into every node property. The top-level `ISRRevision.schema_version` already carries schema identity. Governance must decide whether the node-level field is required for mixed-version subgraphs or is redundant. It must not be silently stripped because it currently affects graph serialization and hash identity.

## 4. Migration proposal

### 4.1 Version transition

- Existing 1.0/1.1 revisions remain immutable and readable under their declared historical version only if they pass that version's validator.
- New revisions using the expanded 14/18 vocabulary are created as 2.0 only after the ADR is approved and the 2.0 validator is implemented.
- No existing content hash, revision ID, source file or evidence record is rewritten.
- A migration creates a new revision identity; it records the old revision ID/hash as parent/derivation provenance and binds the migration tool/version.
- A 1.x revision containing a node/edge kind outside the 9/8 contract is classified as **schema-version mismatch / legacy-invalid**, not silently reinterpreted as valid 1.x. Migration requires explicit review and a new 2.0 revision.

### 4.2 Deterministic migration rules

A migration must:
1. load the exact source revision and verify its original hash;
2. validate the source under its declared historical schema;
3. reject unknown or ambiguous node/edge kinds;
4. preserve all IDs, node/edge properties and graph relationships unless a reviewed mapping explicitly changes them;
5. add or normalize only fields defined by the target schema;
6. emit a complete source-to-target mapping report;
7. validate the target revision under the 2.0 schema;
8. recompute all target identities and hashes;
9. bind source revision, target revision, migration code digest, toolchain and logs in evidence.

There is no generic mapping from `REALIZES`, `CONSTRAINS`, `DERIVES_FROM` or generic `relates_to` from other RequirementGraph variants into ISR edges. Such mappings require their own semantic adapter contract.

## 5. Required implementation and test work

| ID | Work | Acceptance |
|---|---|---|
| ISR-A2-01 | Replace duplicate schema registry definitions with one authority | One registry implementation; imports and package exports tested |
| ISR-A2-02 | Define versioned node/edge schemas and validators | 1.0, 1.1 and proposed 2.0 validators are explicit; unknown versions/types fail closed |
| ISR-A2-03 | Align `ISRRevision.create` with registry | Creation cannot accept an unregistered schema version |
| ISR-A2-04 | Reconcile graph hash vs revision-envelope/provenance hash | D03, code and evidence format agree; deterministic tests prove identity rules |
| ISR-A2-05 | Add 1.0→1.1 and 1.x→2.0 migration tests | Deterministic migration, no source mutation, complete lineage and negative controls |
| ISR-A2-06 | Reconcile producers | TOR, campaign, tests and any stored fixtures declare the schema version matching their actual graph |
| ISR-A2-07 | Reconcile consumers | Lowering, capability checks, conformance, serializers and evidence readers reject unsupported schema versions |
| ISR-A2-08 | Update canonical contract docs | D03, contract registry, R1-D1 inventory/comparison and phase ledger agree with executable code |

## 6. Acceptance gate

Schema remediation is not complete until:
- every node and edge kind has a defined versioned semantic contract;
- edge endpoint compatibility is exhaustive and tested;
- all behavioral payload schemas are versioned and validated;
- graph and revision-envelope identity rules are explicit;
- old revisions remain immutable and reproducible;
- migration is deterministic and loss-reporting;
- every producer and consumer declares/validates schema version;
- unknown versions and semantic losses block before generation;
- independent tests cover positive, negative, boundary and round-trip cases.

## 7. Proposed decision for reviewer

**Recommend approval of the following direction:**
1. `isr/core` remains the sole ISR semantic authority.
2. Preserve the current 14/18 taxonomy and formalize it as schema 2.0 rather than deleting semantic carriers to match stale D03 prose.
3. Keep 1.0 and 1.1 as immutable historical schema contracts; reject 1.x records that use 2.0-only node/edge types.
4. Separate semantic graph content identity from revision/provenance-envelope identity (Option A in §3.2), subject to D03/evidence contract update.
5. Enforce the schema registry in revision construction and all consumers.

**Approval record:** user approved the four FS-00 remediation steps on 2026-11-05. The implementation branch records the schema 2.0 transition, immutable 1.x compatibility, versioned validators/migrations, and separate graph/revision-envelope identities.

**Change boundary:** documentation only. No tests were run because no executable code changed.
