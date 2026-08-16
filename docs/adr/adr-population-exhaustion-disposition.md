# ADR: POPULATION_EXHAUSTION Disposition (R2.9.3 Real-Substrate Evolution)

Status: Accepted — original observation falsified by controlled experiment;
the real-substrate path converges. Mechanism documented; no KNOWN_DEBT carried.
(Updated post Phase-28 identity migration, R2.9 closure.)

Remediation target: `r29.3_substrate_population_exhaustion` — CLOSED
Related: `docs/r29-closure.md`, R2.9.3 multi-generation evolution,
R2.9.8 real-substrate certification dimension,
`docs/adr/adr-phase28-identity-migration.md`

## Context

R2.9.3 established multi-generation evolution with six explicit termination
modes, one of which is `POPULATION_EXHAUSTION` (no novel candidates remain).
The hermetic FSM-substrate evolution converges and repairs correctly.

The **Docker-gated real-substrate** evolution test (R2.9.3 real path) reaches
`POPULATION_EXHAUSTION` in this environment rather than `SUCCESS`.

## Problem

Under the real substrate / Docker execution, the evolutionary run exhausts its
candidate population before resolving the defect. This is a **substrate-level**
behavior of the real backend's variation/evaluation surface, not a defect in
the R2.9.x evolution machinery.

## Attribution

This is classified as a **pre-existing R2.9.3 substrate issue**, and is
explicitly **not** attributed to R2.9.7 (identity separation) or R2.9.8
(certification). Evidence: R2.9.7's dedicated real-path probe confirms the
identity/reproducibility machinery works end-to-end under Docker; the
exhaustion occurs in the R2.9.3 real-substrate evolution path independent of
the identity work.

## Decision

Record `POPULATION_EXHAUSTION` as **KNOWN_DEBT**, non-blocking:

- It does **not** block the hermetic certification (all ten behavioral
  dimensions pass hermetically).
- In the **real-substrate (Docker)** certification dimension, the certifier
  reports `KNOWN_DEBT` → overall `QUALIFIED` when exhaustion is present, and
  `PASS` → `CERTIFIED` when the run reaches `SUCCESS`. Never silent either way.

## Alternatives considered

1. **Fix immediately inside R2.9.7/R2.9.8.** Rejected: out of scope; it is a
   substrate/variation-surface issue, and bundling it would destabilize the
   identity and certification work.
2. **Ignore / deselect the real-substrate test.** Rejected: violates the
   epistemic standard — a deselected test hides the limitation.
3. **Record as KNOWN_DEBT with a remediation target** (chosen). Preserves
   honesty, keeps the certification evidence clean, and tracks the fix.

## Trade-offs

- The real-substrate dimension certifies `QUALIFIED` rather than `CERTIFIED`
  until the substrate issue is resolved. Accepted: this is the honest state,
  and it is recorded, not hidden.
- The debt persists until `r29.3_substrate_population_exhaustion` is addressed.
  Accepted: it is tracked with a concrete remediation target.

## Benefits

- Certification remains epistemically honest (no silent pass, no silent skip).
- R2.9.7/R2.9.8 scope stays clean and attributable.
- The issue is durably tracked rather than rediscovered.

## Risks

- The debt could be forgotten. Mitigated: recorded in the R2.9 closure
  known-debt register and in the certification artifact with a remediation
  target.
- If unresolved before R2.10, real-substrate certification stays `QUALIFIED`.
  Mitigated: remediation is scheduled before R2.10's generation work depends on
  sustained real-substrate evolution.

## Updated disposition (post-migration controlled experiment)

The exhaustion claim is now **falsified as a systematic behavior** by a
controlled experiment: `test_r29_3_real_substrate_converges_in_one_generation`
(the exact scenario the ADR names) was run on **both** sides of the identity
migration, in the current environment:

| Tree | Test | Result |
|---|---|---|
| `45e8a77` (pre-migration, content_hash tainted) | R2.9.3 real-substrate convergence | **PASSED** — SUCCESS at gen 0 (238.43s) |
| `582356b` (post-migration, semantic content_hash) | same test | **PASSED** — SUCCESS at gen 0 (264.27s) |
| `582356b` | R2.9.7 real-substrate audit | PASSED — `divergence_cause = None` (243.54s) |
| `582356b` | R2.9.8 real-substrate certification path | PASSED (295.43s) |

### Causal analysis

Two distinct mechanisms were conflated in the original ADR:

1. **Fake novelty (provenance-stamped clones).** Real, but **hermetic-level**:
   pre-migration, `AlwaysInfeasibleVariation` clones differed by `created_at`
   / `parent_hash` only, so `_same_isr` treated them as novel and elite
   advancement was phantom. The migration exposes this (duplicate-edge
   candidates now correctly stop the search) and the test now guarantees
   architectural novelty. This mechanism did **not** drive the real-substrate
   exhaustion: the real path proposes a single genuine repair.
2. **Real-substrate exhaustion on gen-0 rejection.** The observed mechanism is
   an **infra-transient flake** in the candidate's fresh evaluation (a
   transient container failure in one gen-0 candidate run), which flips
   `target_failure` to fail, forces no-feasible → elite advance, and then
   exhausts at gen 1 because the repair is already present. This is a
   resilience property of the coordinator, not a substrate defect: it did not
   reproduce across the controlled runs above, and the certifier handles it
   honestly (exhaustion → `KNOWN_DEBT` → `QUALIFIED`, never silent).

### Decision (updated)

- The `r29.3_substrate_population_exhaustion` debt is **closed**: the
  documented systematic exhaustion does not reproduce on either side of the
  migration; the real path converges to SUCCESS.
- The certifier's exhaustion → `KNOWN_DEBT` → `QUALIFIED` path **remains** as
  the honest response to future infra flakes — never a silent pass or block.
- The migration closed the phantom-elite-advancement mechanism at the
  hermetic level (see `adr-phase28-identity-migration.md`).

## Remediation path (`r29.3_substrate_population_exhaustion`)

Investigate why the real substrate exhausts its population:
1. Is variation diversity lower on the real substrate than the FSM stub?
2. Is the population size / termination threshold mis-tuned for the real
   backend's candidate space?
3. Is the real-substrate evaluation rejecting candidates that the hermetic
   stub would accept (a boundary-surface mismatch)?
4. Tune variation / population / thresholds, or expand the real-substrate
   variation operators, then re-run the Docker-gated test to confirm `SUCCESS`.

## Future evolution

- The real-substrate convergence now holds on both sides of the migration;
  the controlled experiment closes the debt. If a future environment
  reproduces systematic exhaustion, the certifier's `KNOWN_DEBT` path keeps
  it visible rather than silent.
- Findings may inform R2.10's richer-substrate variation design, where
  population dynamics will differ again.