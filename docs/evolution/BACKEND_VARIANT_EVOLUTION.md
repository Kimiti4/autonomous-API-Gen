# Backend-Variant Evolution for Governed Self-Repair

This document explains the architectural decision behind the CBC-1 governed
self-repair capability: **why** ISR-genome mutation is not used for this
milestone, **why** backend variation is the first valid evolution dimension,
and **how** parent/child trial lineage preserves certification independence.

---

## 1. The constitutional pipeline

```
Requirements
    ↓
ISR                 ← single source of truth (constitutional)
    ↓
Evidence
    ↓
Failure Classification   (cause, not just stage)
    ↓
Learning                 (ContinuousLearningEngine)
    ↓
Evolution                (only when causally actionable)
    ↓
New Candidate
    ↓
Materialize → Plan → Compile → Verify → Deploy → Test
    ↓
New Independent Trial
    ↓
Evidence
```

Self-repair is **governed and auditable**.  It never rewrites evidence, never
patches generated code, and never turns a failed trial into a certified one.

---

## 2. Why ISR-genome mutation is NOT used for this capability

The reference genome is constructed deterministically: its `DecisionSpace` is
effectively **single-valued** (every gene has exactly one valid value).  As a
result, the reference mutation operator, for valid ISR primitives, is a genuine
no-op — it cannot produce a distinct candidate.

Moreover, the ISR invariant layer **correctly rejects implementation
leakage**.  Values such as `postgres`, `jwt`, or `rust-axum` are refused with:

```
ISRInvariantViolation: '<value>' is a compiler backend concern, not an ISR primitive
```

This is a feature, not a bug.  Attempting to evolve the ISR with
implementation-specific variants would **violate the constitutional model**
rather than evolve it.  We do not weaken or bypass these invariants.

> **Decision:** do not mutate the ISR genome to drive self-repair in this
> milestone.

---

## 3. Why backend variation is the first valid evolution dimension

Backend selection is a **compilation strategy**, not an ISR primitive.  The
same ISR (constitutional truth) can be lowered and compiled by multiple
eligible behavioral backend implementations:

```
ISR  H
  ├── backend A → artifact A
  └── backend B → artifact B
```

Both `python-fastapi` and `rust-axum` are eligible behavioral backends.  A
backend swap is therefore a genuine, compilable, independently-measurable
variant that **does not touch the ISR**:

| Identity        | Parent (A)        | Candidate (B) |
| --------------- | ----------------- | ------------- |
| isr_hash        | SAME              | SAME          |
| genome_hash     | SAME              | SAME          |
| intent          | SAME              | SAME          |
| backend_id      | rust-axum         | python-fastapi|
| artifact hash   | `58a9…`           | `1598…` (diff)|
| trial_id        | T1                | T2            |

The ISR/genome hashes are invariant under backend evolution — that invariance
is asserted by the `EVOLUTION_LINEAGE` gate.

---

## 4. Failure stage ≠ failure cause

The classifier distinguishes:

- **observed stage** (build / test / deploy / runtime / …)
- **causal failure class** (infrastructure / compiler / product / unknown)
- **feedback domain**
- **repair eligibility**

For example, a `build` stage failing from a Docker registry outage is
classified as **infrastructure** (LEARN-ONLY), NOT as a lowering/compiler
defect.  This separation is provided by `analyze_failure()` in
`certification/feedback/rule.py`, which uses the causal `failure_class`
(emitted by the real stage classifiers in `docker_stages.py`) rather than the
stage name alone.

---

## 5. Infrastructure failures NEVER trigger backend evolution

If evidence shows registry flakiness, port exhaustion, transient network, or
host resource limits, the failure is infrastructure and:

- produces **learning**,
- remains **immutable evidence**,
- does **NOT** spawn an evolved workload candidate.

This prevents false causal conclusions.  A `rust:1.78-slim` registry outage
must not teach the system "rust is bad for this workload" — it should teach
"the rust registry was temporarily unavailable."  An infrastructure failure is
categorically LEARN-ONLY.

---

## 6. Parent / child trial lineage

Original trials are **immutable**:

```
Trial A  →  FAILED / NOT_CERTIFIED          (never rewritten)
              │
              └── produces candidate B  (a NEW trial)
                      │
                      ▼
                    Trial B  →  CERTIFIED
```

The ledger records the complete causal history as two independent entries:

```
trial-001  origin=reference  backend=rust-axum   result=NOT_CERTIFIED
trial-002  origin=evolved    backend=python-fastapi  parent=trial-001  result=CERTIFIED
```

An evolved trial carries `origin=evolved`, `variant_kind=backend_swap`, a
`parent_trial_id`, a **new** trial id, independent evidence/artifact hashes,
and identical ISR/genome hashes.  The parent is never converted to CERTIFIED
because the child passed.

---

## 7. Certification independence is preserved

Every evolved candidate goes through the **normal pipeline** — there is no
"repair execution" shortcut:

1. allocate a new trial id
2. keep the parent linkage
3. keep the same intent / ISR / genome
4. select the alternate eligible backend
5. compile through the normal backend path
6. verify, deploy, run behavioral tests
7. write independent evidence
8. record `origin=evolved`, `variant_kind=backend_swap`

The `INDEPENDENT_TRIAL_GATE` asserts the child is certified independently of
the parent, and that the parent is unchanged.

---

## 8. Anti-vacuity: evolution must be real, not metadata

Candidate novelty is mandatory.  A backend swap is only accepted if the two
backends produce **different compiled artifacts** for the workload:

```
backend A artifact != backend B artifact
```

If the compiled output is identical, the candidate is rejected with
`NO_OP_EVOLUTION` — creating a new ledger row is not evolution.  This is
enforced by `certification/feedback/execution.py` and the `CANDIDATE_NOVELTY`
gate, and is proven by the D5 Docker trial (image id and artifact hash both
differ).

---

## 9. How future variants plug into the same mechanism

The `EvolutionCandidate` abstraction is intentionally generic.  Later, when the
ISR genuinely gains multiple semantic architectural alternatives, the same
candidate mechanism can support:

```
EvolutionCandidate
├── backend_variant      (this milestone)
├── genome_variant
├── configuration_variant
├── deployment_variant
├── security_variant
└── architecture_variant
```

These are **not** implemented prematurely.  The milestone deliberately delivers
only the backend variant, behind the same governed policy/eligibility/lineage
surface, so the evolution engine does not require redesign when new variant
kinds arrive.

---

## 10. Components

| Module | Purpose |
| ------ | ------- |
| `certification/feedback/rule.py`       | Causal `FailureClassification` + `analyze_failure` (+ legacy `classify_failure`) |
| `certification/feedback/candidate.py`  | `EvolutionCandidate` (ISR-immutable, lineage) |
| `certification/feedback/policy.py`     | `BackendSwapPolicy` + `make_candidate` (auditable eligibility) |
| `certification/feedback/repair.py`     | `GovernedRepair`: classify → learn → decide |
| `certification/feedback/execution.py`  | D5 independent execution + D6 artifact-novelty check |
| `release/gates/cbc1/check_evolution_invariants.py` | D7 certification gate |
| `tests/cbc1/test_repair_loop.py`       | Unit tests (classification, learning, policy, candidate, novelty) |
| `tests/cbc1/d5/`                       | D5 Docker integration trial (`docker_integration` mark) |

---

## 11. Key invariant

> Tiannara can learn from a failure and — when evidence justifies it —
> autonomously construct and evaluate a distinct implementation variant
> **without modifying the constitutional ISR** and **without falsifying the
> original evidence**.

---

## 12. Fullstack capability boundary (D10)

Backend-variant evolution operates exclusively on **backend runtimes**.  The
current Crown Bakery Corpus is entirely backend workloads: 13 categories, 39
intents, two eligible behavioral backends (`python-fastapi`, `rust-axum`).  A
canonical corpus scan shows **zero** frontend/fullstack marker signals, and the
registered backend registry has no frontend implementation.

The governed self-repair loop therefore spans only:

- ISR → backend artifact → container runtime → HTTP behavioral probe
- compile novelty (artifact) · container-image novelty · backend eligibility

It explicitly does **NOT** cover:

- web/SPA/mobile clients
- integration with external UI frameworks
- fullstack deployment topologies (frontend + backend in one bundle)
- frontend behavioral probes (there are none to probe)

This is a **documented capability boundary, not a failure**: the ISR -
requirements graph contains no UI primitives, so the lowering pipeline cannot
manufacture a frontend any more than it can manufacture a mobile app.  When the
corpus later gains fullstack workloads, the same
`FailureClassification → LearningSignal → EvolutionCandidate` mechanism
extends to a `frontend_swap` / `fullstack_topology` variant kind without
redesigning the evolution engine.  Fullstack availability is gated on the
corpus/registry providing real frontend behavior to certify, never on the
evolution loop itself.

See also `docs/capability_boundaries/fullstack.md` for the boundary statement.

---

## 13. Observability

The campaign evolution phase emits a structured, in-process event stream under
`summary.evolution.events` (and the gate emits the same events via
`RepairFeedback.as_record()`):

| Event | Meaning |
| ----- | ------- |
| `feedback.classified`       | a failed trial was classified causally |
| `learning.signal_emitted`   | a LearningSignal entered the ContinuousLearningEngine |
| `evolution.decided`         | the policy accepted/rejected evolution |
| `evolution.candidate_created` | a candidate object was materialized |
| `evolution.novelty_check`   | artifact distinctness was measured |
| `evolution.rejected_noop`   | candidate rejected for identical artifact |
| `evolution.executed`        | candidate submitted as a NEW trial |
| `evolution.parent_immutable`| parent record confirmed unchanged |
| `evolution.certified`       | evolved trial independently certified |

`summary.evolution.signal_count` / `insight_count` expose learning consumption.

---

## 14. Release gates (D9)

The canonical gate set is `release/gates/cbc1/check_self_repair_gates.py`
(`python release/gates/cbc1/check_self_repair_gates.py`).  It runs the ten
named release gates in-process:

CAUSAL_FAILURE_CLASSIFICATION · LEARNING_CONSUMPTION ·
INFRASTRUCTURE_NO_EVOLUTION · BACKEND_ELIGIBILITY · EVOLUTION_LINEAGE ·
ISR_PRESERVATION · ARTIFACT_NOVELTY · INDEPENDENT_TRIAL ·
PARENT_IMMUTABILITY · NO_DIRECT_REPAIR

These complement the existing static gates
(`check_no_direct_repair.py`, `check_certification_independence.py`).
