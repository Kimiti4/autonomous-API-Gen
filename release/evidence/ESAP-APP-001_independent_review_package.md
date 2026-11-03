# ESAP-APP-001 — Independent Review Package

**Review state:** REVIEW_REQUESTED — NOT APPROVED  
**Benchmark:** ESAP-APP-001, version 1.0.0  
**PR:** #201 — Add conservative Android backend and repair Stage A cloud build  
**Review baseline commit:** `f40f8bd2b801cf80178b97f8f3f1b9edd80825a1`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Prepared:** 2026-11-03

> This package is a review aid and decision record. It does not amend the benchmark, freeze its normative files, certify implementation, or record reviewer approval. The reviewer must make and record those decisions after examining the cited source bytes and evidence.

## 1. Requested reviewer role and independence

The user has designated themselves to act as the independent human reviewer for this benchmark review.

The reviewer should confirm before deciding:
- they are reviewing the specification and evidence rather than approving their own implementation work;
- they have no undisclosed conflict that would undermine the independence required by the project;
- the reviewed file identities and hashes below match the files actually inspected;
- any conditions, dissent, or unresolved uncertainty are recorded rather than silently treated as approval.

The implementation author prepared this package and must not submit or impersonate the independent review decision. The reviewer alone completes Section 7.

## 2. Normative benchmark inputs — exact review baseline

These are the current PR-head files. Git blob IDs are Git SHA-1 object identifiers, not SHA-256 digests and not proof of approval.

| Normative input | Path | Git blob SHA-1 | Current declared status |
|---|---|---|---|
| Problem statement | `experiments/android/esap-app-001/PROBLEM.md` | `c074fbaa3d5f9a25c7a0704218c519c0a329ebd5` | Proposed; awaiting independent review and hash freeze |
| Acceptance criteria | `experiments/android/esap-app-001/ACCEPTANCE.json` | `5a6774e3087b8ed0fa2fedffbc502029b0c42c56` | Proposed; awaiting review and hash freeze |
| Benchmark manifest | `experiments/android/esap-app-001/BENCHMARK_MANIFEST.json` | `3934d2c4bc2217df1f39df2656817a0248272ff3` | FROZEN_V1 |

**Status contradiction requiring an explicit decision:** the manifest says `FROZEN_V1`, while both normative artifacts say they are still proposed and awaiting review/hash freeze. The manifest records the first two files' blob IDs correctly, but those IDs establish byte identity only. They do not establish independent review, delegated authority, or approval.

The manifest also states that this benchmark was newly defined because repository searches did not identify an approved Android-specific ESAP-APP-001 problem/acceptance artifact. It is not represented as a previously approved organizational requirement.

No semantic edits to these normative inputs are proposed by this review package. If the reviewer requests a semantic change, create a new benchmark version and new hashes; do not rewrite v1.0.0 in place.

## 3. What the benchmark asks the compiler to prove

The proposed problem is a native Kotlin/Jetpack Compose Android field-inventory application, operating offline, with local durable storage.

The required user workflows include:
- create, view, edit, and delete inventory items, with explicit delete confirmation;
- case-insensitive name-substring search;
- validation of trimmed name (1–80 characters), integer quantity (0–100000), and optional trimmed notes (maximum 500 characters);
- stable item identity and created/updated timestamps;
- durable data across activity recreation and process force-stop/relaunch;
- useful empty, validation, success, and failure feedback;
- primary workflows operating without network access.

The acceptance contract has 13 criteria:
- AC-001 install and launch;
- AC-002 create valid item;
- AC-003 input validation;
- AC-004 edit item;
- AC-005 delete confirmation;
- AC-006 search;
- AC-007 durable persistence;
- AC-008 offline operation;
- AC-009 empty and feedback states;
- AC-010 data integrity;
- AC-011 semantic source traceability;
- AC-012 negative semantic coverage;
- AC-013 reproducibility.

The acceptance policy explicitly requires all criteria to pass, treats unknown as not pass, rejects simulated/static evidence for runtime criteria, binds results to exact source and generated candidate, and disallows partial benchmark certification.

## 4. Current implementation and evidence boundary

At the review baseline, the campaign Android backend is intentionally conservative:
- it implements a structural Android backend and emits a static Compose catalogue shell;
- it declares no executable semantic capabilities;
- it rejects populated service/API/effect/route/interaction semantics and other unsupported behavior rather than silently dropping them;
- the campaign runner binds candidate generation to an ISR revision, compilation plan, and repository hashes, then can run Gradle/APK checks and emulator install/launch;
- the runner's verdict remains structural-only, not benchmark certification.

The current backend therefore cannot generate the full ESAP-APP-001 application described in the problem statement. The workflow infrastructure does not close that gap by itself.

No evidence is currently established for a benchmark APK built from an approved source/ISR candidate, real emulator UI workflows, durable-state assertions, process relaunch, offline operation, independent semantic verification, or full reproducibility. Earlier backend unit-test results and workflow runs are not substitutes for these missing runtime results. A manual cloud workflow dispatch has not been evidenced.

## 5. Architecture and ISR review findings

### 5.1 Existing architecture gates

`folder/prefull.md` defines FS-00 as read-only reconnaissance with four coherent deliverables:
1. Existing Architecture Map;
2. Responsibility Boundaries;
3. ISR/Evolution Audit;
4. Compiler Architecture ADR.

It defines five evidence classes (architectural evidence, contract completeness, boundary integrity, failure/security analysis, migration safety) plus governance approval as the FS-00 exit gate. It says FS-01 follows only after the gate is closed.

The same document says FS-00 is read-only with respect to the existing codebase and limits committed outputs to its prompt and four deliverables. It also says FS-00 findings bind subsequent phases.

**Scope question:** the Android backend PR adds a backend plugin to an existing compiler substrate. The inspected architecture instructions do not conclusively establish whether this benchmark/plugin work is inside the Full-Stack Compiler FS-00/FS-01 implementation gate. This scope must be explicitly decided; neither bypass nor automatic applicability should be assumed.

### 5.2 ISR expressiveness

The current tech-neutral ISR/plan path has typed data, constraints, expressions/invariants, business rules, state transitions, API contracts, authorization rules, and limited frontend route/interaction vocabulary.

The benchmark additionally needs explicit, testable semantics/oracles for at least:
- local case-insensitive substring search;
- durable local persistence and the durability boundary;
- activity recreation and process-death/relaunch lifecycle behavior;
- offline operation and prohibited network dependency/permission;
- user-visible UI states and interaction behavior;
- mapping each requirement to generated components and executable acceptance tests.

A `PERSISTS` relationship alone does not specify durability guarantees or a test oracle. These gaps should be addressed through a reviewed, technology-neutral ISR contract decision, not ad hoc Android-only fields or hidden backend assumptions.

### 5.3 Existing architecture ADR status

At this review baseline:
- `docs/adr/ADR-012-compiler-backend-system.md` is marked **Proposed (pending certification)**.
- `docs/adr/ADR-013-compiler-behavioral-certification.md` is marked **Proposed (pending certification)**.

Their proposals distinguish structural compiler conformance from behavioral execution and call for independent verification. Their status must not be represented as approved merely because the Android PR consumes related interfaces.

## 6. Decisions requested from the independent reviewer

Please decide each item explicitly. A conditional or deferred decision is valid and should identify the condition.

### R1 — Benchmark intent and suitability
Is ESAP-APP-001 v1.0.0 an appropriate intended Stage A Android benchmark for the compiler?

**Recommendation:** Approve its use as the intended benchmark subject to the remaining review decisions; do not describe it as previously mandated or organizationally approved.

### R2 — Problem statement
Do you approve the exact contents of `PROBLEM.md` at blob `c074fbaa3d5f9a25c7a0704218c519c0a329ebd5`?

Check that the workflows, data rules, offline requirement, durability requirement, exclusions, and benchmark-integrity clause express the intended task.

### R3 — Acceptance criteria
Do you approve AC-001 through AC-013 exactly as written in `ACCEPTANCE.json` at blob `5a6774e3087b8ed0fa2fedffbc502029b0c42c56`?

In particular, confirm that runtime criteria require direct candidate-bound emulator evidence, all criteria are mandatory, unknown is not pass, and there is no partial certification.

### R4 — FS-00/FS-01 scope ruling
Does the Full-Stack Compiler FS-00/FS-01 architecture-first gate apply to this Android backend/benchmark work?

**Recommendation:** Complete and record a scope ruling before adding ISR semantics or broadening backend capabilities. If the gate applies, satisfy it; if it does not, record the architectural basis and the applicable alternative governance path.

### R5 — ISR extension direction
Do you authorize preparation of a technology-neutral ISR contract proposal for the missing search, persistence/durability, lifecycle, offline, UI interaction/state, and acceptance-oracle semantics?

**Recommendation:** Authorize proposal and analysis only at this review stage. Treat any normative ISR schema change as a separate reviewed decision; do not smuggle it into Android backend code.

### R6 — Implementation scope
Do you authorize implementation after the architecture/ISR decisions are approved: source-faithful Android generation, explicit backend capability declarations, candidate-bound independent verification, native UI/lifecycle/offline test harness, and evidence capture?

**Recommendation:** Yes, with fail-closed capability handling and no weakening of AC-001..AC-013.

### R7 — Freeze/status reconciliation
After R2/R3 are approved and the review decision is recorded, may the benchmark authority update the manifest and normative status fields to a consistent reviewed/frozen state, retaining a durable decision record and exact hashes?

**Recommendation:** Yes, only after approval; preserve v1.0.0 bytes if accepted unchanged. If changed semantically, issue a new version and hashes.

## 7. Independent reviewer decision record — to be completed by reviewer

**Reviewer identity:** ____________________________________  
**Review date/time (UTC):** ______________________________  
**Independence / conflict statement:** _____________________  
**Exact reviewed problem blob:** ___________________________  
**Exact reviewed acceptance blob:** _______________________  
**Exact reviewed manifest blob:** _________________________

For each decision R1–R7, record one: `APPROVE`, `REJECT`, or `DEFER`, with rationale and conditions.

| Decision | Reviewer verdict | Rationale / conditions |
|---|---|---|
| R1 — Benchmark intent | | |
| R2 — Problem statement |APPROVED | |
| R3 — Acceptance criteria |APPROVED | |
| R4 — FS-00/FS-01 scope |APPROVED |Complete and record a scope ruling before adding ISR semantics or broadening backend capabilities. If the gate applies, satisfy it; if it does not, record the architectural basis and the applicable alternative governance path. |
| R5 — ISR proposal direction |APPROVED | |
| R6 — Implementation scope |APPROVED | |
| R7 — Freeze/status reconciliation |APPROVED | |

**Overall review outcome:** `APPROVED` / `REJECTED` / `DEFERRED`

**Required corrections or conditions:**  
________________________________________________________________  
________________________________________________________________

**Reviewer decision evidence reference:** _________________________

**Reviewer confirmation:** I reviewed the exact source artifacts and hashes recorded above. My decision applies only to the decisions explicitly marked above and does not certify compiler implementation or benchmark execution.

## 8. Post-review actions (not performed by this document)

1. Preserve this review record and the exact reviewed file hashes.
2. Resolve any rejected/deferred items; obtain a new review if normative files change.
3. Record the FS-00/FS-01 scope ruling and architecture/ISR decisions.
4. Only after approval, reconcile benchmark status and freeze metadata without rewriting accepted bytes.
5. Implement the approved ISR/backend/verifier changes.
6. Run the manual cloud build and real emulator acceptance suite against an immutable, approved source revision.
7. Have the independent reviewer inspect candidate-bound evidence for every AC-001..AC-013 criterion.
8. Keep Stage A BLOCKED until every mandatory criterion has direct evidence and the independent verification decision is recorded.

## 9. Current verdict

**Stage A: BLOCKED.**

This review package is prepared, not approved. The Android structural slice and cloud workflow foundation do not yet constitute the ESAP-APP-001 application or a passing benchmark. No APK, runtime acceptance result, independent verification result, or benchmark certification is claimed here.


## 10. Reviewer decisions recorded — partial approval (2026-11-03)

The independent reviewer communicated the following decisions in the project conversation on 2026-11-03:

| Decision | Recorded verdict | Basis |
|---|---|---|
| R2 — Problem statement | **APPROVED** | Reviewer explicitly approved R2 at the exact v1.0.0 baseline recorded in Section 2. |
| R3 — Acceptance criteria | **APPROVED** | Reviewer explicitly approved R3: AC-001 through AC-013 and their strict evidence policy. |
| R4 — FS-00/FS-01 scope | **APPROVED — gate applies** | Reviewer approved the recommendation to apply the architecture-first gate to this Android compiler target before further ISR/backend semantic expansion. |

This is a partial decision record only. R1, R5, R6, and R7 remain unapproved/unresolved. No PR review event has been submitted on behalf of the reviewer. This record reflects the reviewer's explicit conversational decision; it is not a GitHub APPROVE review and does not certify implementation.

### R4 scope ruling and consequence

**Scope ruling:** The FS-00/FS-01 architecture-first gate applies to ESAP-APP-001 Android backend work. The Android emitter is a compiler backend target in the Full-Stack Compiler architecture, and changes needed to represent the benchmark's missing semantics would affect the technology-neutral ISR/compiler boundary. Treating those changes as an isolated Android plugin implementation would bypass the architecture decision the gate is intended to protect.

**Evidence basis:** `folder/prefull.md` defines FS-00 as read-only architecture reconnaissance and requires four coherent deliverables: Existing Architecture Map, Responsibility Boundaries, ISR/Evolution Audit, and Compiler Architecture ADR. It requires five evidence classes plus governance approval before FS-01. It states that FS-00 findings bind subsequent phases and that compiler code is not to be written ahead of the architecture decision. The current branch tree contains no `tiannara/application/compiler/fs00/` directory and no path matching the four deliverable titles/names. This is a bounded path/tree check, not proof that no differently named or external artifact exists; however, no qualifying committed, coherent, reviewed FS-00 package was located in this repository snapshot.

**Gate status:** `FOUNDATION_NOT_READY` / NOT EVIDENCED COMPLETE. This is not a claim that no prior architectural work exists; it is a finding that the required four deliverables and governance approval record have not been established by the evidence located at this baseline.

**Authorized next work:** proceed with read-only FS-00 reconnaissance and prepare the four required deliverables. Do not extend normative ISR schemas, widen Android backend capabilities, or implement benchmark-specific semantics until the FS-00 evidence converges and the required governance approval is recorded. Existing Android structural foundation code is not retroactively certified by this ruling.

### Normative benchmark handling

R2 and R3 approve the contents of the exact v1.0.0 problem and acceptance artifacts identified in Section 2. Their bytes must remain unchanged. The manifest's `FROZEN_V1` status still conflicts with the problem and acceptance files' proposed/unreviewed status. Do not reconcile those status fields or claim a formal freeze until the remaining applicable review/authority decisions are resolved and the durable freeze record is prepared under R7.
