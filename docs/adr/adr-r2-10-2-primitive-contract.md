# ADR: R2.10.2 — ISR Primitive Design & Dependency Ordering

- **Status:** EXECUTED
- **Commits:** see R2.9 closure record
- **Related:** ADR `adr-phase28-identity-migration.md` (migration pattern reused),
  ADR `adr-population-exhaustion-disposition.md`

## Context

R2.10.1 (capability/expressivity audit) attested a signed matrix: **2
EXPRESSED, 18 PARTIAL, 0 PROJECTED, 10 MISSING** (matrix hash `8cfb4c90…`,
pre-migration). The 10 MISSING capabilities have no ISR carrier at all:

`architecture_boundaries`, `behavior_temporal_semantics`,
`business_capabilities`, `data_migrations`, `deployment_rollout_rollback`,
`documentation`, `evolution_objectives_protected_regions`,
`reliability_resilience`, `requirements_acceptance_traceability`,
`testing_anchoring`.

R2.10.2 is the design-and-contract slice: it specifies the primitives,
derives their dependency order, defines how the ISR may be extended without
contaminating it with technology, and defines what "evolvable" means for each
— BEFORE any schema change. Restraint over opportunistic growth.

## Decision 1 — schema extension strategy: Option A (omit-empty projection)

Adding fields to the ISR schema changes `asdict`-based projections for every
existing ISR (empty new fields appear as `[]`/`null`). Three options:

| Option | Mechanism | Verdict |
|---|---|---|
| **A** | `canonical_form` omits empty carriers (None, "", [], (), {}); one-time migration recomputes hashes; afterwards adding *optional* primitives is hash-stable forever | **CHOSEN** |
| B | `schema_version` + projection dispatch | Rejected: permanent dispatch complexity |
| C | accept hash churn per addition | Rejected: repeated disruption across a 10-primitive backlog |

**Adopted:** A. `canonical_form` in
`constitutional_architecture/isr/semantics/projection.py` (the single source
of truth) now omits empty carriers inside containers. Booleans, zero, and
non-empty strings remain meaningful. This is the projection rule every new
primitive inherits: an empty optional primitive is identity-neutral; a
non-empty one is hash-sensitive (governance change-detection preserved).

### Migration record (before/after gates, Phase-28 pattern)

- **Rule:** `canonicalize({a:1, b:"", c:[], d:None, e:{}}) == canonicalize({a:1})`.
- **Extension-stability:** an ISR with an empty optional carrier hashes
  identically to the same ISR without it.
- **Change-detection preserved:** entity-only edits still move `content_hash`
  (entity/deployment/policy-only edits re-verified).
- **Provenance isolation preserved:** `created_at`/`parent_hash`/`version`
  still never taint the hash.
- **Semantic stability:** `content_hash == semantic_content_hash` across
  recomputes; `stable_isr_hash` unchanged in behavior.
- **Phase-28 migration gates:** 13/13 pass post-migration.
- **Full hermetic suite:** 1784 passed, 2 skipped, 7 Docker-gated deselected.
- **R2.10.1 matrix re-attested:** same 2/18/0/10 split; new matrix hash
  `317b62a8…` (semantics unchanged, identity rule changed).
- No test asserted a literal pre-migration hash (all identity assertions are
  relationship-based), so the migration was mechanical.

## Decision 2 — the ten primitives and their derived dependency order

Each primitive is fully specified (semantic meaning, ownership, dependencies,
constraints, mutation surface, validation surface, compiler projection,
evidence projection, lineage requirements, intended type signature) in
`tiannara/application/evolution/primitive_contract.py`.

The dependency graph is **derived mechanically**, not hand-drawn:

```
A depends on B  iff  A.type_signature references B      (structural)
                  or A.mutation surface requires B      (mutation)
                  or A.validation rules reference B     (validation)
                  or A.compiler projection derives B    (projection)
```

Derived edges (asserted acyclic; topological order below):

```
requirements_acceptance_traceability <- business_capabilities
architecture_boundaries              <- business_capabilities
reliability_resilience               <- behavior_temporal_semantics
deployment_rollout_rollback          <- data_migrations, reliability_resilience
testing_anchoring                    <- requirements_acceptance_traceability
documentation                        <- 8 of 9 (everything but objectives)
evolution_objectives_protected_regions <- all 9 others (protects genes that must exist)
```

**Derived implementation order:**

```
behavior_temporal_semantics
→ business_capabilities
→ data_migrations
→ reliability_resilience
→ architecture_boundaries
→ requirements_acceptance_traceability
→ deployment_rollout_rollback
→ testing_anchoring
→ documentation
→ evolution_objectives_protected_regions
```

**What the derived graph refutes in the original sketch:** "requirements
first" — capability declarations (`business_capabilities`) precede
traceability (`requirements_acceptance_traceability`), because trace links
target capabilities. The requirement *nodes* themselves arrive with R2.10.4's
Requirement Graph → ISR construction (the unbuilt top half); the ISR-side
entry point is the capability registry + trace links. The sketch's chain
"requirements → capabilities → boundaries → evolution constraints" survives
as edges (capabilities before boundaries; objectives last), but temporal/data
semantics are roots and may be built in parallel with the cluster, not after
it. The derived graph is the authority.

## Decision 3 — technology-agnostic lint (mechanical, not by review)

`assert_technology_agnostic` runs as a gate over every primitive
specification (id, meaning, ownership, every surface, every type signature
name/body). `TECHNOLOGY_COUPLING_TERMS` covers frameworks, datastores,
messaging, infrastructure, security mechanisms, and observability vendors
(e.g. `postgresql_config` fails; `persistence_semantics` passes). The two
highest-risk primitives are constrained to intent: `deployment_rollout_rollback`
expresses promotion/reversal *semantics*; `data_migrations` expresses
version-transition *semantics* — Kubernetes/Alembic-style realization lives in
compiler backends.

## Decision 4 — evolution-readiness progression gates EXPRESSED on locality

Each primitive declares completion criteria for every stage of

```
MISSING → REPRESENTED → VALIDATED → MUTATABLE → COMPILABLE
→ OBSERVABLE → LINEAGE_TRACKED → EXPRESSED
```

`EXPRESSED` requires the R2.10.1 **mutation-locality proof** (mutating the
gene leaves every other gene's semantic hash unchanged) — the difference
between "we added a field" and "we added an evolvable gene."

## Decision 5 — extension contract

Six rules every new primitive must satisfy before implementation: the
projection rule (Option A), the probe rule (new gene ⇒ new capability probe +
`gene_index` entries in the R2.10.1 audit), the locality rule (EXPRESSED ⇒
locality proof), the tech-agnostic rule (lint gate), the compatibility rule
(old ISR ⇒ same semantic hash ⇒ same artifact ⇒ same evolution behavior), and
the readiness rule (all stages declared before implementation).

## Compatibility contract (proven, not assumed)

- **Same semantic hash:** old-style FSM ISRs keep identity relationships
  (`content_hash == semantic_content_hash`, provenance-neutral).
- **Same compiler artifact:** `async_resolution_module` output is byte-identical
  for the same ISR (codegen untouched by the projection migration).
- **Same evolution behavior:** await-stripping still rejected and await-add
  still allowed by `AwaitingSurfaceIntactInvariant` pre-execution; Phase-28
  gates green.

## Evidence

- `tests/test_r29_10_2_primitive_contract.py` — 23 tests: specification
  completeness, lint (positive + negative), derived graph (mechanically
  derived, acyclic, topologically valid, unknown-ref rejected), extension
  contract rules, readiness matrix (all stages, locality-gated EXPRESSED),
  migration gates, compatibility contract, ledger attestation, determinism.
- Contract attested in the ledger as `PRIMITIVE_CONTRACT` event
  (content-hashed, chain-anchored, R2.8.14 pattern); contract content hash
  `f7b8901b…`.
- Full hermetic suite: **1784 passed, 2 skipped, 7 Docker-gated deselected**
  (189.87s).

## Consequences

- R2.10.3 may implement primitives in the derived order — roots first
  (`behavior_temporal_semantics`, `business_capabilities`, `data_migrations`),
  each gated by the extension contract and its readiness targets, with the
  audit matrix re-attested after every primitive lands.
- `documentation` and `evolution_objectives_protected_regions` are the natural
  final cluster; objectives cannot be meaningfully declared before the genes
  they protect exist.
- The 18 PARTIAL capabilities remain untouched (R2.10.3/4 gene-level work) —
  diagnostic-to-remedial discipline preserved.