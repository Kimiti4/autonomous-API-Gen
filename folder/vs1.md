# VS-1 — FIRST END-TO-END VERTICAL SLICE

## AUTHORITATIVE MASTER PROMPT (DRAFT — AWAITING APPROVAL)

**Repository:** `Kimiti4/autonomous-API-Gen`
**Branch:** `main`
**Accepted baseline:** `71a65ae` (Post-R1-D Reconciliation: RECONCILED — DOWNSTREAM IMPLEMENTATION DEFERRED)
**Required prior state:** R1-B PASS, R1-C PASS, R1-D.1 PASS, R1-D.2 PASS, R1-D.3 PASS, Reconciliation PASS
**Purpose:** Prove the reconciled substrate can produce ONE real, deployed, observable, verifiable, evolvable full-stack product
**Slice product:** Task-tracking CRUD SaaS (one category, one representative product)
**Slice backend:** Python FastAPI + Postgres (canonical pair)

---

# 0. MANDATE

You are operating as the **Tiannara Vertical Slice Architect and Implementation Auditor**.

R1-D established ONE ISR authority, ONE Compiler IR contract, ONE Evolution authority, and the reconciliation gate proved they compose. VS-1 must now prove the composition **executes end-to-end on a real product**:

```text
                 ONE REAL PRODUCT (task-tracking CRUD SaaS)
                       │
                       ▼
                 Requirements
                       │
                       ▼
                RequirementGraph
                       │
                       ▼
                     ISR
                       │
                       ▼
             Architecture Candidates
                    /       \
                   /         \
             Candidate A   Candidate B
                   \         /
                    Evaluation
                       │
                    Selection
                       │
                       ▼
             Canonical Compiler IR
                       │
                       ▼
              Backend (FastAPI + Postgres)
                       │
                       ▼
                  ArtifactSet
                       │
                       ▼
                  Verification
                       │
                       ▼
                   Deployment
                       │
                       ▼
              Runtime Observation
                       │
                       ▼
                  Evaluation
                       │
                       ▼
                   Evolution
                       │
                       └───────────────↺ (second candidate)
```

The success criterion is NOT "an app was generated." It is:

> **Requirement → Architecture → Software → Evidence → Evolution.**

The slice must demonstrate the first genuine Tiannara autonomous software-engineering loop on a real deployed product.

This is an **implementation phase**, unlike the reconciliation gate. Production code WILL change. But every change must trace to the reconciled contracts.

---

# 1. CONSTITUTIONAL PRINCIPLES (immutable during VS-1)

## P1 — ISR remains the semantic source of truth (`isr/core/`)

No slice activity may establish another ISR authority.

## P2 — Category is a capability, not an authority

Task-tracking is a parameter/capability of the general compiler architecture:

```text
Category
   ↓
Capability / Profile
   ↓
Architecture
   ↓
Compiler
   ↓
Backend
   ↓
ArtifactSet
```

Do NOT create `TaskCompiler`, `CrudCompiler`, or any category-specific semantic authority. A second category later must reuse this path.

## P3 — Compiler/evolution separation (reconciliation §17)

Evolution decides what architecture to try. The compiler decides how that architecture becomes software. Neither assumes the other's responsibility.

## P4 — Lineage is mandatory and complete

Every artifact in the slice must preserve:

```text
Requirement
   ↓
RequirementGraph
   ↓
ISR
   ↓
ArchitectureCandidate
   ↓
EvolutionOperation
   ↓
CompilerIR
   ↓
ArtifactSet
   ↓
VerificationResult
   ↓
Deployment
   ↓
RuntimeObservation
   ↓
Evaluation
   ↓
EvolutionRecord
   ↓
New ArchitectureCandidate
```

An artifact that cannot trace this chain is not a Tiannara-generated artifact.

## P5 — Verification is downstream of the artifact; certification never manufactures evidence

Fail-closed direction preserved at every layer (reconciliation §14).

## P6 — Historical evidence is immutable

B3-v2, `certification/`, `release/evidence/`, historical ledgers: untouched except by explicit append-only new-campaign records under a NEW campaign identity. Never rewrite.

---

# 2. SCOPE

## VS-01 — Slice requirements + RequirementGraph

One real product requirement set for task-tracking (users, tasks, CRUD, authN/authZ at minimum). Structured RequirementGraph in `reqgraph/core`. Manual intake is acceptable; autonomous intake is NOT required.

## VS-02 — Canonical ISR for the slice

One `isr/core` ISR revision for the product. Technology-neutral. No FastAPI/Postgres/Docker leakage (existing `FORBIDDEN_IMPLEMENTATION_TERMS` + `TESTING_MECHANISM_TERMS` enforced).

## VS-03 — Two architecture candidates + evaluation + selection

Candidates A and B from the ISR via `evolution/core` (construction + operators). Documented evaluation, explicit selection decision, lineage records. Real crossover/mutation semantics; no pseudo-operations.

## VS-04 — Compiler IR + backend lowering

Selected candidate → canonical Compiler IR path (`isr_to_plan` + contract refinements where implemented) → `PythonFastAPIBackend` → `GeneratedRepository`/ArtifactSet. Backend constraints/capabilities explicit. No filesystem writes inside `compile()` (R1-C C06 invariant).

## VS-05 — Verification of the generated artifact

Structural conformance + build + start + health + CRUD contract checks against the ACTUAL generated boundary (reconciliation §21). Fail-closed; INDETERMINATE never becomes CERTIFIED.

## VS-06 — Deployment (local, reproducible)

One reproducible deployment path (Docker Compose preferred, matching campaign precedent). No cloud deployment required. Deployment descriptor is an artifact with provenance, not tribal knowledge.

## VS-07 — Runtime observation boundary (first implementation of D12)

Minimal observation surface that retains reverse lineage (deployment → ArtifactSet → CompilerIR → Architecture → ISR → RequirementGraph). This is the first runtime implementation of the D12 contract; it stays minimal and does NOT reconstruct `autonomous-api` (C-17 remains deferred except for this narrow boundary).

## VS-08 — Second-loop evolution proof

At least one observed→evaluated→selected→new-candidate transition recorded with full lineage (EvolutionRecord). Proves the loop closes; does not require autonomous redeployment.

## VS-09 — Slice lineage audit + gate

Complete lineage audit of every slice artifact + gate report with verdict.

---

# 3. OUT OF SCOPE (explicit; do not build)

```text
13 remaining portfolio categories / generators
second backend in the slice (Rust Axum stays regression-covered, not deployed here)
cloud deployment (AWS/Azure/GCP)
frontend framework beyond minimal API-verifiable surface (React/Vite deferred)
autonomous coding agent / self-modification
new evolution algorithms / population scaling / distributed evolution
Observatory redesign
knowledge/civilization redesign
packaging cleanup (C-18)
B3-v2 rerun; certification evidence rewrite
performance optimization
```

If any appears necessary: classify DEFERRED with rationale unless it is a constitutional contradiction (then STOP and escalate).

---

# 4. BASELINE GATE (before any implementation)

1. Branch `main`; HEAD `71a65ae`; `origin/main` in sync.
2. Working tree clean for tracked files.
3. R1-D.1/D.2/D.3 + Reconciliation PASS artifacts present.
4. B3-v2 + `certification/` + `release/evidence/` untouched.
5. Combined baseline green (404 passed, 1 pre-existing deselection).
6. R1-RG-01–RG-12 present.

If the baseline differs materially: STOP with a discrepancy report.

---

# 5. EVIDENCE STANDARD (from reconciliation §6)

Priority: executed runtime path > passing tests > direct callers > imports > static implementation > contracts > docs > naming. Every claimed edge classified RUNTIME_PROVEN / TEST_PROVEN / STATIC_ONLY / DOCUMENTED_ONLY / UNKNOWN. Never claim runtime composition from contracts alone. Distinguish CONTRACTUALLY READY from IMPLEMENTED (§23).

---

# 6. REQUIRED DELIVERABLES

## VS-D01 — Slice requirements + graph (`folder/VS1_REQUIREMENTS.md`)

Real product requirements; RequirementGraph construction; manual-intake rationale.

## VS-D02 — Slice ISR (`isr/` revision + `folder/VS1_ISR.md`)

Canonical ISR revision for the product; technology-neutrality evidence (invariant run output).

## VS-D03 — Candidates + selection (`folder/VS1_CANDIDATES.md`)

A/B construction, evaluation scores, selection decision, lineage records.

## VS-D04 — Compilation + backend (`folder/VS1_COMPILATION.md`)

IR, backend lowering, capability/constraint matching, ArtifactSet manifest + hashes.

## VS-D05 — Verification (`folder/VS1_VERIFICATION.md`)

Build/start/health/CRUD evidence; fail-closed handling of every failure.

## VS-D06 — Deployment (`folder/VS1_DEPLOYMENT.md` + reproducible descriptor)

One-command reproducible local deployment; descriptor under version control with provenance.

## VS-D07 — Observation boundary (`folder/VS1_OBSERVATION.md`)

Minimal D12 implementation; reverse-lineage fields; C-17 boundary respected (no `autonomous-api` resurrection).

## VS-D08 — Second-loop evolution (`folder/VS1_EVOLUTION_LOOP.md`)

Observed → evaluated → selected → new candidate, with EvolutionRecord.

## VS-D09 — Lineage audit (`folder/VS1_LINEAGE_AUDIT.md`)

Full Requirement → New Candidate chain per artifact; gaps explicitly marked.

## VS-D10 — Test report (`folder/VS1_TEST_REPORT.md`)

Baseline suites + new slice tests; exact commands and counts; no weakened assertions.

## VS-D11 — Gate report (`folder/VS1_GATE_REPORT.md`)

GATE QUESTIONS below with YES/NO + evidence. Verdict: SLICE_PROVEN / NOT_PROVEN / BLOCKED.

---

# 7. TEST REQUIREMENTS

New `tests/vs1/` tier (orthogonal to Tier-A/R1-C/R1-D/rg tiers):

- Contract: slice ISR valid; candidate references ISR; IR references candidate; backend consumes IR; artifact manifest complete + hashed.
- Composition: ISR→Genome→materialized ISR→plan→repo chain executable in-test.
- Backend: FastAPI repo builds; app starts; health + CRUD contracts pass (local Docker-gated where required, skippable with explicit reason outside Docker hosts).
- Lineage: parent→child; artifact→candidate; record→operation; observation→artifact fields present.
- Failure: invalid ISR rejected; unsupported capability → INDETERMINATE → not certified; verification exception → INDETERMINATE.
- Regression: full baseline stays green; no Tier-A/R1-D/rg weakening.

---

# 8. GATE QUESTIONS (all mandatory for SLICE_PROVEN)

## Ownership (must all be YES)

- G01 RequirementGraph authority unambiguous in the slice?
- G02 ISR authority (`isr/core`) preserved, no leakage?
- G03 Architecture candidate authority unambiguous?
- G04 Compiler IR authority preserved (no BIR promotion)?
- G05 Evolution authority preserved (no second engine)?
- G06 Backend consumed IR without redefining upstream semantics?
- G07 ArtifactSet is the generated boundary (no out-of-band emission)?

## Forward slice (must all be YES)

- G08 Requirements → RequirementGraph without bypass?
- G09 ISR technology-neutral (invariant run clean)?
- G10 Two candidates constructed + evaluated + selection recorded?
- G11 Selected candidate → Compiler IR → Backend → ArtifactSet executable?
- G12 Generated FastAPI app builds?
- G13 Generated app starts and serves health?
- G14 CRUD contracts pass against the running app?
- G15 Verification evidence recorded fail-closed?

## Deployment + observation (must all be YES)

- G16 Deployment reproducible from version-controlled descriptor?
- G17 Observation retains reverse lineage to artifact/IR/candidate/ISR?
- G18 No `autonomous-api` resurrection beyond the narrow D12 boundary?

## Evolution closure (must all be YES)

- G19 At least one observation → evaluation → selection → new candidate transition recorded?
- G20 EvolutionRecord preserves parent/operation/child lineage?
- G21 New candidate re-enters the compiler path (or is shown re-enterable by construction)?

## Integrity (must all be YES)

- G22 Historical evidence untouched (B3-v2, ledgers)?
- G23 No second ISR/CompilerIR/Evolution authority introduced?
- G24 No category-specific semantic authority created for task-tracking?
- G25 Baseline suites green with no weakened tests?
- G26 All gaps explicitly classified (no silent DEFER)?

## Final

- G27 Full Requirement → New Candidate lineage traversable per artifact?
- G28 Substrate needed no constitutional redesign to host the slice?
- G29 Next category can reuse this path (capability/profile, not new authority)?
- G30 Slice demonstrates Requirement → Architecture → Software → Evidence → Evolution?

## Verdicts

```text
SLICE_PROVEN — all G01–G30 YES; downstream portfolio expansion authorized in principle
NOT_PROVEN — slice incomplete; targeted remediation scoped
BLOCKED — constitutional contradiction; substrate must be revisited
```

---

# 9. STOP CONDITIONS (immediate STOP + blocker report)

1. ISR/CompilerIR/Evolution authority would change.
2. A second provenance/lineage authority becomes necessary.
3. Historical ledger/B3-v2/certification evidence would be modified.
4. A bidirectional adapter becomes necessary.
5. A category-specific semantic authority becomes necessary.
6. Full 14-category build becomes necessary to answer the gate.
7. Existing tests must be weakened.
8. An R4/R5 contradiction appears.
9. Production rewrite beyond the slice boundary becomes necessary.
10. Evidence cannot distinguish implemented from merely contracted behavior.

---

# 10. COMMIT DISCIPLINE

Grouped commits, scoped to VS-1:

```text
VS-D01/D02 (requirements + ISR)
VS-D03 (candidates + selection)
VS-D04/VS-D05 (compilation + verification)
VS-D06/VS-D07 (deployment + observation)
VS-D08/D09/D10/D11 (evolution loop + lineage + tests + gate)
```

No history rewrite, no force-push, no B3-v2 touch, no unrelated changes. Push only under explicit per-group authorization.

---

# 11. HARD STOP

After the VS-1 gate report: STOP. No second category, no portfolio expansion, no self-engineering. Portfolio breadth requires a separate authorization informed by the VS-1 gate.

---

# 12. STATUS

**DRAFT — AWAITING APPROVAL.** No implementation has begun under this prompt. Baseline remains `71a65ae`. Nothing in this file authorizes code changes; authorization requires your explicit "Proceed with VS-1" referencing this prompt version.
