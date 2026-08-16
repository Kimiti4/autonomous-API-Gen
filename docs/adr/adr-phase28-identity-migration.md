# ADR: Phase-28 Identity Migration (Semantic / Provenance / Runtime Separation)

Status: EXECUTED — migration applied and compatibility-gated (R2.9.8 closure)

Related: `docs/r29-closure.md`, `tiannara/application/evolution/identity.py`,
`tiannara/application/evolution/reproducibility_audit.py`,
`constitutional_architecture/isr/semantics/projection.py`,
`tests/test_phase28_migration_gates.py`

## Context

The Intermediate Software Representation (ISR) is the constitutional source of
truth. Its identity must therefore be stable and content-derived. Across six
phases — R2.3, R2.4, R2.8, R2.9.4, R2.9.5, R2.9.6 — the same defect surfaced
repeatedly: **volatile provenance (`created_at`) leaking into the semantic
content hash**, making cross-run ISR identity unstable.

R2.9.7 reproduced the defect empirically and established a three-identity model
(`identity.py`) that computes a stable `semantic_hash` without modifying the
Phase-28 ISR model.

## Problem

Phase-28's `ISR.content_hash` is computed over the whole ISR, including
provenance fields (`created_at`, `parent_hash`). Consequently:

- Two architecturally-identical ISRs with different `created_at` have
  different `content_hash`.
- Cross-run replay fails: identical evolution inputs produce diverging
  `content_hash` trajectories from generation 1 onward.
- The "source of truth" is unstable, violating the foundational principle.

R2.9.7's audit demonstrated this:
```
semantic_reproducible = true
content_reproducible  = false
divergence_cause      = provenance_volatility   (compounds at gen ≥ 1)
```

## Decision

Adopt a **three-identity model** and migrate Phase-28's `content_hash` to be
semantic-only. The migration is **executed** and gated by dedicated
compatibility evidence (see Migration record below).

The three identities, which must never be conflated:

```
semantic_hash          = H(canonical(Semantic Architecture))
provenance_identity    = lineage (parent, mutation source, evolution, created_at)
runtime_execution_id   = execution-instance identity
```

## Alternatives considered

1. **Exclude-list hash** (hash everything except known-volatile fields).
   Rejected: defines architecture negatively as "everything except what we
   currently know is volatile"; silently rots when R2.10 introduces richer
   graphs with new volatile fields; nested volatility can leak.
2. **Fold `created_at` into a deterministic value** (e.g., zero it).
   Rejected: destroys legitimate provenance information; treats the symptom.
3. **Inclusion-based semantic projection** (chosen). The projector explicitly
   defines what architecture *is* on a substrate; provenance/runtime are never
   projected. Extensible: R2.10's Component/Requirement graphs get their own
   projector.

## Trade-offs

- **Inclusion-based projection requires a substrate-specific projector.**
  Accepted: this is explicit schema definition, which is the point. It is
  replaceable per substrate (protocol + dependency injection).
- **Deferring the Phase-28 migration leaves `content_hash` temporarily tainted.**
  Accepted: R2.9.x reproducibility uses `semantic_hash` immediately; the debt
  is recorded as `KNOWN_DEBT` with a remediation target, not hidden.

## Benefits

- Stable semantic identity → true cross-run reproducibility.
- Provenance preserved (lineage intact) but separated from semantic identity.
- The recurring six-phase leak is structurally eliminated, not patched.
- R2.10's richer ISR can extend the projection without re-auditing an
  exclusion list.

## Risks

- **Migration touches every consumer comparing `content_hash` for reproducibility.**
  Mitigated: gate the migration behind before/after compatibility evidence.
- **A substrate projector could over-exclude, achieving false stability.**
  Mitigated: R2.9.7's negative test (an architectural change must change
  `semantic_hash`) guards against this.

## Migration plan (executed)

1. **Audit proves the defect** — DONE (R2.9.7).
2. **`ISR.content_hash` recomputed via the semantic projection** — DONE. The
   projection lives in `constitutional_architecture/isr/semantics/projection.py`
   (the constitutional single source of truth): a full recursive canonicalization
   of the architectural tree (`System` and everything nested), with
   `version` / `provenance` / `_content_hash` structurally excluded. It is NOT
   routed through `ISRSerializer` (no `default=str` fallback); unhandled types
   raise `CanonicalizationError`.
3. **`created_at` / `parent_hash` remain in `provenance`** — unchanged; they
   feed lineage only, never the semantic hash.
4. **Consumers updated** — `identity.FSMSemanticProjector` delegates to the
   projection; `stable_isr_hash` collapses onto `semantic_content_hash`;
   `ReproducibilityAuditor` taint is evidence-based (`tainted = phase28 is not
   None and phase28 != semantic`), never a provenance-presence heuristic.
5. **Gated on before/after compatibility evidence** — all gates green
   (`tests/test_phase28_migration_gates.py`, 13 passed):
   - architectural change detection intact (entity / deployment / policy-only
     changes move the hash),
   - `created_at` and `version` isolated,
   - `content_hash == semantic_hash == stable_isr_hash` on every substrate,
   - `content_reproducible` flips to `true` (audit + cross-run + long horizon),
   - gen ≥ 1 parent binding is stable across runs,
   - lineage chain valid and causal integrity preserved
     (`CausalGate.fresh` recompile equivalence),
   - no R2.8/R2.9.x regression (hermetic R2.9.6/7/8 subprocess gate).

## Migration record (verification evidence)

- Migration gates: **13 passed** in 253s.
- Hermetic R2.9.x regression (R2.9.6/7/8, Docker tests deselected): **41 passed, 2 deselected**.
- R2.9.7 real-substrate (Docker) audit: **passed** (243.54s) —
  `divergence_cause = None`, `content_reproducible = true` under real execution.
- R2.9.8 real-substrate certification path: **passed** (295.43s).
- Full hermetic suite (`python -m pytest`, 7 Docker-gated tests deselected):
  **1744 passed, 2 skipped, 7 deselected** (811.88s).
- Post-migration invariant on every substrate:
  `content_hash == semantic_hash == stable_isr_hash`; R2.9.7's audit now reports
  `phase28_tainted_by_provenance = false`, `taint_fields = ()`, and the R2.9.8
  `provenance_content_identity` / `phase28_identity_migration` dimensions are
  closed as PASS (see `docs/r29-closure.md`).
- Test adjustments reflecting the corrected semantics: R2.9.7's conflation
  demonstrations flipped to equality assertions; R2.9.3's
  `AlwaysInfeasibleVariation` now guarantees architectural novelty per
  generation (seed-unique trigger) so elite advancement is real, not
  provenance-fabricated.

## Future evolution

- R2.10 introduces Component/Requirement graphs → a new `SemanticProjector`
  implementation, injected into `IdentityExtractor`, not a change to the model.
- The `provenance_content_identity` KNOWN_DEBT and `phase28_identity_migration`
  NOT_CERTIFIED entries in the R2.9.8 certification are **closed as PASS**
  (non-mandatory dimensions, both PASS post-migration).