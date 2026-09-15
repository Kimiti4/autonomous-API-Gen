# FS-00 — Full-Stack Compiler Architectural Reconnaissance & Foundation Gate

**Status:** Constitutional entry point. The first artifact of the Full-Stack Compiler era. Not an implementation plan — a *governance* plan that decides what implementation is allowed to be planned.

**Authority:** The `folder/masterprompt.md` (Tiannara — Autonomous Full-Stack Software Engineering & Evolution Engine) governs this document. Where masterprompt is silent, the Phase 31 spec (`folder/31.md`) and its `PHASE31_EXECUTION_CONTRACT.md` continue to apply.

**Predecessor state:** Phase 31 is functionally closed. The three cross-cutting gaps are implemented and covered by Tier A (243 passed in `tests/cbc1`):
* Cost/energy fitness axis → 18 tests
* Governance registry → 19 tests
* Escalation policy → 24 tests

B3-v2 is running autonomously. The certification architecture is frozen.

---

## 1. The rule that governs everything below

> **`masterprompt.md` should govern the construction of this system; it should not itself become the implementation plan.**

The Full-Stack Compiler is the architectural response to masterprompt §6. Its construction is governed by masterprompt. This document does not *re-state* masterprompt. It *operationalizes* the parts of masterprompt that govern the Full-Stack Compiler: it names the acceptance criterion, the sequencing, the responsibilities, and the entry/exit gates of the next phase of work.

If a future contributor reads only this document, they should know:
1. What the Full-Stack Compiler must do (acceptance criterion).
2. What work is forbidden before FS-00 is done (anti-patterns).
3. What FS-00 itself produces and how it is gated.
4. What comes after FS-00, in the order it must come.

Everything else is downstream.

---

## 2. The first hard acceptance criterion

> **Given a technology-neutral, validated ISR, Tiannara can deterministically lower it through Compiler IR into one complete full-stack application, verify that application, produce immutable provenance/evidence, and expose the complete lineage from requirement to deployed artifact.**

Decomposed into observable properties:

* **ISR is technology-neutral.** The lowerer never sees `react`, `fastapi`, `postgres`, `docker`, `aws`, `k8s`, etc. as inputs. (Masterprompt §3.)
* **Lowering is deterministic.** The same ISR + same Compiler IR + same backend selection + same seed produces byte-identical full-stack artifacts. (Phase 31 spec §"Stratify, don't just multiply" and §38 Certification Execution.)
* **The lowering surface is `Compiler IR`**, not the ISR directly. The ISR never becomes a frontend/backend/infra artifact; the IR does. (Masterprompt §6: "Tiannara must support generation of complete software products. A full-stack candidate may contain: frontend, backend, database, authentication, authorization, API, background workers, messaging, object storage, caching, infrastructure, deployment manifests, CI/CD, observability, documentation, tests".)
* **Verification gates the lowering.** A lowered artifact that fails verification does not pass; it is quarantined. (Masterprompt §15: 17-level verification pipeline; Phase 31 `PHASE31_EXECUTION_CONTRACT.md` §3 anti-vacuity.)
* **Evidence is immutable.** Every lowering step, every gate, every artifact hash, every lineage edge is recorded in the evidence chain. (Masterprompt §26, §38; Phase 31 `infra_storm` and `EvolutionLedger` design.)
* **Lineage is end-to-end.** An auditor can trace from `requirement_id` → `requirement_graph_node` → `isr_node` → `compiler_ir_node` → `backend_artifact` → `deployed_instance`. (Masterprompt §18: traceability; Phase 31 spec §"Cross-Cutting Gaps" #1: CertificationEvidence schema.)

Until this acceptance criterion is **demonstrably** met (not just architecturally possible), the Full-Stack Compiler is not done.

---

## 3. The architecture-first sequencing

FS-00 is the only entry point. Implementation does not start until FS-00 is signed off. The work between Phase 31 closeout and the first compile is sequenced to make each step auditable and reversible.

```text
B3-v2 (running)
   │
   ▼
Phase 31 Final Verdict
   │
   ▼
Phase 31 Closeout
   │
   ▼
┌──────────────────────┐
│ FS-00 Reconnaissance │
└──────────┬───────────┘
           ▼
   Existing Architecture Map
           │
           ▼
   Responsibility Boundaries
           │
           ▼
   ISR / Evolution Audit
           │
           ▼
   Compiler Architecture ADR
           │
           ▼
   ISR ↔ Compiler IR Contract
           │
           ▼
   Compiler Orchestration Contract
           │
           ▼
   Backend / Artifact Contracts
           │
           ▼
   First Vertical Compiler Slice
```

Each box is a deliverable. Each transition is a gate. No step is optional. No step is parallel with another (the order is the reason the order is the order).

### 3.1 Phase 31 Closeout (gate before FS-00)

* Verify the B3-v2 final verdict (CERTIFIED / NOT_CERTIFIED / QUALIFIED_PARTIAL).
* Record the verdict in the Certification Governance registry (`certification/governance/registry.py`).
* Detect any regressions via `CertificationGovernanceRegistry.detect_regressions()`.
* Capture the wave's `cost_energy` aggregate (mean wall-clock, mean cost-efficiency, peak resource per backend).
* Capture the wave's `infra_storm` summary (if any infrastructure failures were observed; LEARN-ONLY).
* Emit a `Phase 31 Closeout` ADR (or extension to the existing `adr-phase28-constitutional-governance-closure.md`).
* **Gate:** Closeout ADR is on disk and committed. If the verdict is `NOT_CERTIFIED` for budget-exhaustion reasons (the expected outcome for B3 at 12hr), the closeout is still valid; the verdict is honest, not a defect.

### 3.2 FS-00 Reconnaissance (this document's first hard deliverable)

FS-00 is **non-mutating**. It produces:
* An `Existing Architecture Map` (a structural inventory of what Tiannara already has).
* A `Responsibility Boundaries` document (which module belongs to which architectural concern).
* An `ISR / Evolution Audit` (does the current ISR shape support the Full-Stack Compiler acceptance criterion?).
* A `Compiler Architecture ADR` (the proposed Compiler IR + lowering boundary, with alternatives considered and rejected).

FS-00 is a reading exercise, not a writing exercise. The output is four documents, no code. The output is reviewed against the masterprompt and either accepted or sent back for revision.

**Gate:** All four FS-00 documents are on disk, committed, and reviewed. The Compiler Architecture ADR is approved.

### 3.3 ISR ↔ Compiler IR Contract (FS-01)

Defines the boundary between the ISR and the Compiler IR. The contract is:
* The set of node kinds the ISR may emit.
* The set of node kinds the Compiler IR may emit.
* The transformation rules (which are deterministic, which are parametric, which are policy-gated).
* The schema_id / schema_version for both sides.
* The serialization (canonical form) for both sides.
* The hash function (so an ISR hash and an IR hash are both reproducible and chain-anchored).

**Gate:** The contract is on disk, has a version, and is bound by an ADR. No compiler code is written until this contract is approved.

### 3.4 Compiler Orchestration Contract (FS-02)

Defines the public surface of the compiler. A `CompilerOrchestrator` (or equivalent) that takes a validated ISR + a backend selection policy and produces a full-stack artifact. The orchestrator's contract:
* Inputs (what it accepts; what it rejects; what it escalates).
* Outputs (what it produces; how lineage is recorded).
* Failure modes (what it does when a backend fails; what it does when evidence is corrupted).
* Composition rules (how backend artifacts are combined into a full-stack artifact).

**Gate:** The orchestrator's contract is on disk. The orchestrator itself is not yet implemented; the contract is the blueprint.

### 3.5 Backend / Artifact Contracts (FS-03)

One contract per backend family (frontend, backend, data, auth, infrastructure, integrations, deployment). The contract for each:
* The set of node kinds the backend consumes from the Compiler IR.
* The set of artifacts the backend emits.
* The verification surface (what gates run on the backend's artifacts).
* The test surface (what tests run on the backend's artifacts).
* The evidence surface (what evidence the backend emits).

**Gate:** Each contract is on disk, has a version, and is bound by an ADR.

### 3.6 First Vertical Compiler Slice (FS-04)

A single end-to-end compilation: one ISR → one full-stack artifact. The slice is intentionally narrow:
* One ISR (a single technology-neutral requirement).
* One backend selection (the simplest one that produces a real full-stack artifact).
* One deployment target (local; not production).
* One certification verdict (CERTIFIED / NOT_CERTIFIED / QUALIFIED_PARTIAL).
* One evidence chain.
* One lineage trace from requirement to deployed artifact.

**Gate:** The first vertical slice produces a real artifact, with a real verdict, with a real evidence chain, with a real lineage trace. The slice is a *demonstration* of the acceptance criterion in §2.

---

## 4. Forbidden moves before FS-00 is signed off

These are anti-patterns. They are listed here so a future contributor can recognize them and stop.

* **Do not create a new top-level `compiler/fullstack/` directory yet.** The Compiler IR boundary is decided in FS-00. Until it is, the directory tree is a guess.
* **Do not start a frontend compiler (React, TypeScript, WASM, etc.).** Frontend is a backend family in masterprompt §7. It is a contract in FS-03, not a module.
* **Do not introduce a new ISR primitive.** The current ISR shape is frozen until the ISR / Evolution Audit (FS-00) decides what to extend.
* **Do not write a generator that emits code without a hash-chained evidence trail.** Masterprompt §27 anti-vacuity. Every generated artifact must trace back to a requirement and an ISR node.
* **Do not refactor for aesthetics.** "Refactor toward explicit architectural boundaries; do not refactor merely for aesthetics." If a module doesn't clearly belong somewhere, that is an architectural finding to record, not a reason to move files.
* **Do not commit changes while B3-v2 is running unless they are clearly outside the wave's runtime surface.** The wave's verdict ledger is sacred. Touching `certification/`, `release/evidence/`, or the B3 wave's process while it runs is forbidden.
* **Do not assume the current architecture is the right one.** FS-00 may surface findings that require restructuring. The phase ordering is `audit → decide → restructure → implement`, not `implement → audit → refactor`.

---

## 5. Module classification (one-line per existing module — full classification in FS-00)

Every existing module in this repository should be classifiable as one of:

* **ISR** — the constitutional source of truth (`constitutional_architecture/isr/`).
* **Requirement Intelligence** — Requirement Graph + LLM-driven intent compilation (`tiannara/application/intent/`, `tiannara/application/cap_a_*`).
* **Evolution Engine** — candidate generation, mutation, fitness, multi-generation, selection (`tiannara/application/evolution/`, `tiannara/application/self_improvement/`, `tiannara/application/learning/`).
* **Compiler** — ISR-to-artifact lowering (`compiler/`, `tiannara/application/compiler/`).
* **Verification** — gates, integrity, conformance, evidence (`tiannara/application/compilation/consumption_contract.py`, `tiannara/application/quality/`, `certification/stages/`).
* **Certification** — campaign, decision, governance (`certification/`, `tiannara/application/campaign/`).
* **Evidence / Provenance** — ledgers, lineage, provenance bundles (`tiannara/application/evolution/ledger.py`, `certification/evidence/`, `tiannara/application/provenance/`).
* **Infrastructure** — Docker, port, sandbox, GitHub, ledger files (`tiannara/infrastructure/`, `compiler/backends/production/`).
* **Plugin** — registry, contracts, protocols that other backends plug into (`compiler/core/protocol.py`, `tiannara/application/identity/`).
* **Generated Software** — anything under `generated/`, `autonomous-api/`, `constitutional_architecture/generated/`, `tiannara/frontend/` (the latter is the *intended* location for the fullstack frontend, currently out of scope).

If a module doesn't clearly belong, FS-00 records that as an architectural finding.

---

## 6. Anti-pattern: treating masterprompt as a backlog

masterprompt is not a backlog. It is a constitution. The difference matters:

* A backlog is a list of things to do. You cross items off and stop when the list is empty.
* A constitution is a set of constraints. You do work that *complies* with the constraints, and you stop when the work is *done*, not when the list is empty.

A backlog encourages completing items for the sake of completing them. A constitution encourages completing work only when the work satisfies the constraints. The Full-Stack Compiler is finished when it satisfies the acceptance criterion in §2 — not when a number of files have been written.

If a contributor finds themselves saying "we should write a frontend compiler next" without being able to point to which acceptance-criterion clause that work satisfies, they are working from a backlog, not a constitution. The right response is to return to §2 and identify the clause.

---

## 7. Operational rules during FS-00

* FS-00 is **read-only** with respect to the existing codebase. No file is added, removed, or renamed in the existing tree. The output is a set of new documents under `tiannara/application/compiler/fs00/` (or equivalent) that *describe* the existing tree.
* The new documents are themselves subject to the `.md` policy: only the FS-00 prompt and its four deliverables (architecture map, responsibility boundaries, ISR/Evolution audit, Compiler ADR) are committed. Internal notes and discovery artifacts are kept in the working tree but not tracked.
* FS-00 may take multiple sessions. There is no "one shot" expectation.
* FS-00's findings are *binding* for FS-01 onwards. If FS-00 says the Compiler IR boundary should sit between `tiannara.application.intent` and `tiannara.application.compiler`, FS-01 designs the contract at that boundary, not somewhere else.
* B3-v2 may complete during FS-00. If it does, the closeout in §3.1 is performed before FS-00 is signed off. The verdict feeds the ISR/Evolution audit.

---

## 8. The first hard question FS-00 must answer

> **Where does the Compiler IR boundary sit?**

Four candidate locations, with their trade-offs:

1. **Between `intent` and `compiler`.** Lower the ISR directly into backend-specific artifacts. Simple, but loses the polymorphic-backend property the masterprompt wants.
2. **Between `compiler` and `backends/`.** Each backend is a "backend family" (frontend, backend, data, etc.) that consumes a generic IR. Polymorphic. Requires defining the IR shape.
3. **Between `evolution` and `compiler`.** The Evolution Engine emits an Architecture Candidate (genome) that the Compiler consumes. The Architecture Candidate is the IR. Implies the Evolution Engine has compiler-shaped output.
4. **After `compiler`, before `verification`.** The Compiler emits a full-stack artifact; verification gates it. The IR is the compilation's internal form, not an architectural boundary.

FS-00's Compiler Architecture ADR must pick one (or argue for a new fifth location) and explain why. The choice cascades into FS-01 (the IR contract) and FS-02 (the orchestrator's contract).

The pick is not a code decision — it is a *constitutional* decision. The chosen boundary becomes the architectural seam the rest of the Full-Stack Compiler is built around. It is the hardest decision in the project and it must be made before any compiler code is written.

---

## 9. What FS-00 is NOT

To prevent scope creep:

* FS-00 is not a code refactor. It produces documents, not PRs.
* FS-00 is not a spec for the Full-Stack Compiler. The spec is masterprompt. FS-00 is a *reading* of masterprompt against the existing tree.
* FS-00 is not a benchmark. The Full-Stack Compiler is not done when a benchmark passes; it is done when the acceptance criterion in §2 is demonstrated.
* FS-00 is not a kickoff. The kickoff is the first vertical slice (FS-04). FS-00 is the *gate before the kickoff*.
* FS-00 does not consume the B3 verdict. The verdict is the *input* to FS-00's ISR/Evolution Audit, not the *output* of FS-00.

---

## 10. Exit criteria for FS-00

FS-00's exit is a **gate** with five independent evidence classes plus a governance step. Each class is separately checkable; none of them alone is sufficient. The five classes must converge before FS-00 is closed. Closing the gate is what authorizes FS-01; closing the gate is also what authorizes a `git commit` of the FS-00 artifacts.

The decomposition exists because **git state records an architectural decision; it does not prove the architectural decision is correct.** A clean commit history can still encode a wrong boundary. The five-class gate separates "we wrote the documents and committed them" from "the documents actually demonstrate the architecture is sound."

```text
ARCHITECTURAL EVIDENCE
        +
CONTRACT COMPLETENESS
        +
BOUNDARY INTEGRITY
        +
FAILURE / SECURITY ANALYSIS
        +
MIGRATION SAFETY
        +
GOVERNANCE APPROVAL
        ↓
FS-00 FOUNDATION_READY
```

Then:

```text
FOUNDATION_READY
        ↓
commit approved FS-00 artifacts
        ↓
FS-01 authorized
```

FS-00 returns one of two values:

* `FOUNDATION_READY` — all five classes are met and governance has approved. FS-01 is authorized.
* `FOUNDATION_NOT_READY` — at least one class is unmet. The output names which class failed and what the next action is. FS-00 is re-iterated, not bypassed.

### 10.1 Architectural Evidence

The four FS-00 documents exist, are committed, and are coherent with each other. The documents are:

1. **Existing Architecture Map** — every module under `tiannara/`, `compiler/`, `constitutional_architecture/`, `certification/`, `learning/`, `knowledge/`, `evolution/`, `autonomous-api/`, and `generated/` is listed and classified per §5.
2. **Responsibility Boundaries** — every concern in §5 has exactly one owning module, or the document records the gap as a finding.
3. **ISR / Evolution Audit** — answers: does the current ISR shape support the acceptance criterion in §2? If not, what must change? (The audit may recommend waiting for B3-v2's verdict before deciding.)
4. **Compiler Architecture ADR** — picks the Compiler IR boundary per §8, explains the pick, lists the rejected alternatives, and names the *consequences* of the pick (what the next phase must do because of this choice).

Coherence means: the four documents reference each other consistently. A boundary named in the Architecture Map is also named in the Responsibility Boundaries. The Compiler IR boundary picked in the ADR is the one the ISR/Evolution Audit assumes. There are no contradictions.

### 10.2 Contract Completeness

The contracts that FS-01, FS-02, FS-03 will design in detail are *named* in the FS-00 documents, with their inputs, outputs, failure modes, and verification surfaces sketched. FS-00 does not write the contracts; FS-00 ensures the contracts are *visible* so FS-01 knows what to design.

A contract is "visible" when:

* its name is in the Architecture Map or Responsibility Boundaries,
* its inputs and outputs are listed,
* its failure modes are listed (what does it do when the system is in an unknown state),
* its verification surface is named (what gates run on the contract's outputs),
* its evidence surface is named (what evidence is emitted when the contract is exercised).

A contract that is "name only" without the four points above is a finding, not a contract.

### 10.3 Boundary Integrity

The Compiler IR boundary chosen in §8 is *demonstrated* against the existing tree. A boundary that is described in the ADR but cannot be located in the existing code is an architectural claim without a substrate. The boundary integrity check:

* locates the boundary in the existing tree (a file, a directory, or a set of files),
* names the modules on each side of the boundary,
* enumerates the dependencies crossing the boundary,
* flags any dependency that crosses the boundary in the wrong direction (e.g. an ISR module importing from a backend family).

The boundary integrity check is the most concrete artifact FS-00 produces. It is the *evidence* that the architecture is real, not aspirational.

### 10.4 Failure / Security Analysis

The chosen boundary is analyzed for failure modes and security surface. The analysis answers:

* What happens to the system if a backend fails compilation? (The boundary must degrade, not crash.)
* What happens to the system if evidence is corrupted? (The boundary must not pass artifacts past a broken chain.)
* What happens to the system if the ISR contains an unknown primitive? (The boundary must escalate, not silently pass.)
* What is the threat model? (Who can submit an ISR? Who can submit a backend? Who can read evidence? Who can publish? The answers become the authz surface.)
* What secrets are emitted in evidence? (The boundary must redact.)

This analysis is informed by the existing `certification/governance/escalation_policy.py` and the existing ledger-verify logic. The analysis is not a re-design; it is an *application* of the existing patterns to the new boundary.

### 10.5 Migration Safety

If FS-00 finds that the existing tree does not match the chosen boundary, the migration plan must be safe. The migration safety check:

* lists the files that must move,
* lists the imports that must change,
* names the order in which the changes can be applied (so that no intermediate state is broken),
* identifies the tests that must pass at each intermediate state,
* names the rollback path (how to revert if the migration fails partway).

Migration safety is the bridge between "we know what we want" (the ADR) and "we can get there" (the implementation). A boundary that requires a 100-file atomic move with no rollback is a *finding*, not a decision — FS-00 must either find a safer boundary or document the risk explicitly.

### 10.6 Governance Approval

All five evidence classes are met. The four documents are coherent. The boundary is real, not aspirational. The failure modes are analyzed. The migration is safe. *Then* a human reviewer (or the lead architect) approves.

Approval is a recorded action, not an implicit state. The approval is one of:

* `APPROVED — proceed to FS-01` (or equivalent wording in the approval record),
* `REJECTED — fix class X and re-submit` (with a specific class to fix),
* `DEFERRED — wait for B3-v2 verdict` (only valid if the rejection is conditional on the B3 verdict).

Approval is recorded in the Certification Governance registry (`certification/governance/registry.py`) as a record with `phase_id = "fs00_approval"`, `attempt_id = <date>`, `verdict = "CERTIFIED"` (or equivalent). The record's `evidence_refs` list the FS-00 documents. The record's `metrics` include the verdict class (which of the five classes was the binding constraint) and the per-class pass/fail.

### 10.7 What the gate explicitly is NOT

* It is **not** "the documents are committed." A commit is a step in the gate, not the gate itself.
* It is **not** "the human reviewer signed off." Approval is a step in the gate, not the gate itself.
* It is **not** "all tests pass." FS-00 produces no code; it produces documents. The tests for FS-00 are the *five-class checks themselves*, not code tests.
* It is **not** "B3-v2 has finished." B3-v2 is an input to the ISR/Evolution Audit, not a prerequisite for closing the gate. The audit may recommend waiting for B3-v2, but the gate does not require it.

The gate is `FOUNDATION_READY` iff:

* All five evidence classes (10.1 through 10.5) are met, and
* A `CERTIFIED` record exists in the Certification Governance registry for `phase_id = "fs00_approval"`, and
* The record's `evidence_refs` list all four documents, and
* No `NOT_CERTIFIED` record exists in the registry for the same `phase_id` and `attempt_id` (no regression).

Until all four are true, FS-00 is not done. The git commit of the FS-00 artifacts is *part of* the closing action, not a substitute for it.

---

## 11. The single sentence that rules the project

> **Tiannara is not a code generator. Tiannara is an autonomous software engineering system that can be trusted to generate code.**

Every decision — what to build, what not to build, what to refactor, what to leave alone, what to test, what to certify, what to escalate, what to publish, what to roll back — is in service of that sentence.

The Full-Stack Compiler is the next chapter. FS-00 is the gate before the chapter. Phase 31 is the chapter before this one, and it is closed.
