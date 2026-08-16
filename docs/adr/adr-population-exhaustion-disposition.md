# ADR: POPULATION_EXHAUSTION Disposition (R2.9.3 Real-Substrate Evolution)

Status: Accepted — KNOWN_DEBT, non-blocking (R2.9.8)

Remediation target: `r29.3_substrate_population_exhaustion`
Related: `docs/r29-closure.md`, R2.9.3 multi-generation evolution,
R2.9.8 real-substrate certification dimension

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

- Once the real substrate converges, the certification dimension flips to
  `PASS` and the KNOWN_DEBT entry closes.
- Findings may inform R2.10's richer-substrate variation design, where
  population dynamics will differ again.