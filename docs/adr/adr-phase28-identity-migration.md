# ADR: Phase-28 Identity Migration (Semantic / Provenance / Runtime Separation)

Status: Accepted — migration deferred, separately gated (R2.9.7)

Related: `docs/r29-closure.md`, `tiannara/application/evolution/identity.py`,
`tiannara/application/evolution/reproducibility_audit.py`

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

R2.9.7's audit demonstrates this:
```
semantic_reproducible = true
content_reproducible  = false
divergence_cause      = provenance_volatility   (compounds at gen ≥ 1)
```

## Decision

Adopt a **three-identity model** and migrate Phase-28's `content_hash` to be
semantic-only. The migration is **deferred and separately gated** from R2.9.

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

## Migration plan (when executed)

1. **Audit proves the defect** — DONE (R2.9.7).
2. **Recompute `ISR.content_hash` via the semantic projection**, excluding
   provenance/runtime.
3. **Move `created_at` and `parent_hash` into the `provenance` structure.**
4. **Update consumers** that compare `content_hash` for reproducibility to use
   the semantic identity; consumers needing lineage use `provenance` explicitly.
5. **Gate on before/after compatibility evidence:**
   - lineage chain remains valid,
   - causal integrity preserved (`CausalGate.fresh` recompile equivalence),
   - `content_reproducible` flips to `true` under the R2.9.7 audit,
   - no R2.8/R2.9.x regression.

## Future evolution

- R2.10 introduces Component/Requirement graphs → a new `SemanticProjector`
  implementation, injected into `IdentityExtractor`, not a change to the model.
- Once migrated, the `provenance_content_identity` KNOWN_DEBT and
  `phase28_identity_migration` NOT_CERTIFIED entries in the R2.9.8
  certification can be re-evaluated and closed.