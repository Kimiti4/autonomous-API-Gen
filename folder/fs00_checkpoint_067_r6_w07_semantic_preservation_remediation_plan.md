# FS-00 Checkpoint CP067-R6 (plan) — W07 Semantic-Preservation Remediation Plan

**Disambiguation:** Implementation checkpoint **CP067-R6** already records **R1-W06 / B-04**. This artifact is **`CP067-R6-W07-PLAN`** — **planning and ratification only**. **No production code changes** until authority gates below are satisfied.

**Status:** **`PLANNING_ONLY`** — awaits human ratification before implementation authorization.

**Machine register:** `certification/atlas/esap/cp067_r6_w07_semantic_preservation_plan.json`

**Ratification template:** `release/evidence/cp067_r6_w07_plan_ratification_TEMPLATE.json` (not ratified until signed)

---

## 0. Governance constraints (preserved)

| Constraint | Value |
| --- | --- |
| R1-W03 `verification_status` | **`PARTIALLY_VERIFIED`** — unchanged by this plan |
| R1-W08 `verification_status` | **`PARTIALLY_VERIFIED`** — unchanged by this plan |
| W08 ingress matrix | **No expansion** authorized by this plan |
| CP068 | **`CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`** |
| Implementation | **Forbidden** until `plan_ratification.status == RATIFIED` |

---

## 1. ADR-R1-03 reconciliation

| Field | ADR-R1-03 record | Current register / evidence | Gap |
| --- | --- | --- | --- |
| `governance_status` | `APPROVED` (2026-11-08 ratification) | `cp067_r2_human_adr_ratification_2026-11-08.json` | None |
| `decision_status` | `APPROVED` | Same | None |
| `implementation_status` | **`NOT_IMPLEMENTED`** (ADR header) | **Partial:** contract registry + W07 IV slice shipped | **Reconcile:** ADR header stale vs repo; plan ratification must either amend ADR metadata or document scoped partial implementation under W06/W07 without claiming ADR complete |
| `verification_status` | **`NOT_VERIFIED`** (ADR header) | W07 harness `passed` on **minimum set** only | ADR IV not satisfied until B-03 replay + obligation adversarial corpus |
| `related work packages` | **R1-W06** only | R1 register **W07** = evidence-graph (ISR-009); delivered work = **ADR-R1-03 bridge slice** | **Authority:** this plan treats **W07 semantic-preservation** as ADR-R1-03 continuation; **does not** authorize CP063 graph-identity scope without separate ratification |
| Prerequisite ADRs | R1-01, R1-02 | W01/W02 IV complete (Payroll slice) | Sufficient for **plan**; synthesized paths need CP065 linkage |
| Minimum bridges | B-03, B-04, B-07, B-08, B-09 | All registered in `transformation_contracts.py` | **B-03** has method id only — **no independent replay harness** |
| Authority to implement | R1-W06 authorized | W07 `PARTIALLY_VERIFIED` | **Next implementation** requires **this plan ratified** + explicit B-03 slice authorization |

**Plan authority gate G1:** Human owner ratifies this document + plan JSON. **G2:** Supplement or amend ADR-R1-03 `implementation_status` / `verification_status` to reflect scoped partial vs remaining work (no silent full approve).

---

## 2. W07 partial evidence — precise gaps

**Existing evidence:** `release/evidence/cp067_w07_bridge_semantic_evidence_report.json` — registry completeness, B-04 oracle (payroll), B-07 fail-closed.

| Delivered | Not delivered |
| --- | --- |
| TransformationContract for B-03…B-09 | ≥22 CP067 bridges |
| `synthesis-obligation-preservation-v1` **method id** on B-03 | **Executable** B-03 replay verifier |
| B-04 obligation diff on 3 workloads (via W10) | B-03 on 3 workloads |
| Lossiness policy for trusted compile | Obligation **adversarial** matrix (dropped/altered/duplicated/unsupported) |
| W10 gate `W07-ADR-R1-03-BRIDGE-EVIDENCE` | Evidence-graph **invalidation** bindings (register W07 P2 track) |
| CP065 payroll synthesis tests (separate checkpoint) | CP065 **bound into** B-03 IV evidence artifact |

**Closure assessment pointer:** `cp067_r5_w03_closure_w10_assessment_report.json` — recommends **W07 before W08 matrix expansion**.

---

## 3. Bounded B-03 obligation-replay slice (proposed)

**Scope (phase 1 only):**

| Dimension | Bound |
| --- | --- |
| Workloads | `payroll`, `orders`, `appointments` (human + **synthesized** path where `synthesize_for_workload` exists) |
| Source family | `reqgraph.synthesis` → `engineering_synthesizer` output + TOR provenance |
| Destination family | `isr.core.revision.ISRRevision` |
| Source identity | `synthesis_run_id`, TOR digest, reviewer verdict ref (CP059 JSONL when present) |
| Destination identity | `revision_id`, `content_hash`, `ISRRevision.schema_version` |
| Bridge contract | `B-03` v1.0.0, `LOSSY_EXPLICIT`, verification method **`synthesis-obligation-preservation-v1`** |
| Replay procedure | (1) Re-synthesize workload → `ISRRevision`. (2) Extract obligation carriers: auth policy ids, validation nodes, effect edges, operation identity keys. (3) Compare to golden obligation snapshot **or** prior replay row (content-addressed JSONL). (4) Fail closed on any missing critical obligation. |
| Independent verifier (future) | `certification.isr_independent_verification.b03_synthesis_obligation_replay.v1` |

**Explicit exclusions:** inventory/projects full synthesis parity; constitutional F-06 path; EngISR (B-08/B-09).

---

## 4. Inverse plan→ISR limits

| Direction | Authorized | Behavior |
| --- | --- | --- |
| ISR → plan (B-04) | **Yes** (trusted, lossy explicit) | Existing `b04_lowering_obligation_verifier` + plan binding gate |
| plan → ISR compiler | **No** | Governed paths **must fail closed** (`PlanBindingError` / bridge-not-trusted) |
| Reconstructible from plan alone | Behavioral op ids, lowered auth refs, effect bindings **as audit inventory** | Via forward lowering replay only — not semantic round-trip proof |
| **Not** reconstructible | Graph topology, requirement_ref materialization, constitutional envelopes, synthesis provenance | Listed in B-04 `lossy_axes`; silent recovery **forbidden** |
| Digest substitution | plan digest ≠ ISR hash interchangeability | Already enforced at W04 binding + B-07 |

**Plan gate G3:** No `plan_to_isr` module on trusted orchestration/publication path without new ADR + ratification.

---

## 5. Adversarial obligation cases (required before W07 IV closure)

| Case | Mutation | Expected result |
| --- | --- | --- |
| Dropped authZ | Remove security policy node from synthesized graph before replay compare | **FAIL** — critical obligation |
| Altered validation | Change validation constraint payload, preserve node id | **FAIL** — obligation drift |
| Duplicated operation | Duplicate API node with same operation key | **FAIL** or explicit dedup policy (documented) |
| Unsupported family | Inject node type outside synthesis contract | **FAIL** — `UNSUPPORTED_FAIL_CLOSED` |
| Loss budget breach | Add lossy node type smuggled into behavioral set | **FAIL** — B-04 + B-03 cross-check |

Corpus location (future): `tests/bridges/test_b03_synthesis_obligation_adversarial.py` — **not authorized until plan ratified**.

---

## 6. Independent-verification criteria & evidence-graph bindings

**W07 may advance to `INDEPENDENTLY_VERIFIED` only when all hold:**

1. B-03 replay harness **passed** on 3-workload slice (synthesized path).
2. Adversarial table (section 5) — **minimum 5 cases** automated.
3. Evidence artifact `cp067_w07_b03_obligation_replay_report.json` with `verifier_id`, per-workload rows, obligation fingerprints.
4. **Evidence-graph bindings** (CP063 slice, not full graph program):
   - Link synthesis run → ISR `content_hash` → plan digest → B-04 report row.
   - Reference CP065 obligation HTTP slice where applicable (`requirement_oracle_bindings`).
5. Human supplement ratification (pattern: ISR-002/004 supplements) **or** plan execution ratification binding finding **002/004** scoped acceptance criterion **`b03-obligation-replay-v1`**.
6. W03/W08 statuses **unchanged** unless separate checkpoint.
7. CP068 remains conditional.

**Does not require:** universal ISR, full 22-bridge matrix, dashboard ingress `IMPLEMENTED`.

---

## 7. Dependency graph — next work after ratification

```text
[Ratify this plan] → [Authorize B-03 implementation slice only]
                 → [W07 IV closure attempt]
                 → (parallel, not blocking) R1 register W07 evidence-graph track — separate ratification
                 → W08 dashboard parity — **not** authorized here
                 → CP068 — **not** authorized
```

**Recommended implementation order post-ratification:** B-03 replay harness → adversarial tests → evidence JSON → W10 gate row → governance supplement.

---

## Ratification record (pending)

| Approver | *(pending)* |
| Evidence | `release/evidence/cp067_r6_w07_plan_ratification_YYYY-MM-DD.json` |
| `implementation_authorized` | **false** until ratified |
