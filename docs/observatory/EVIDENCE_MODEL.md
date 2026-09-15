# Observatory Evidence Model

## Binding

Every displayed material claim resolves to one of:

1. **Authoritative runtime state** (live subsystem query, identity noted),
2. **Evidence record** (hash-bound artifact with provenance chain), or
3. **Explicit epistemic state** (`:unknown`, `:not_measured`,
   `:not_applicable` — rendered as such).

There is no fourth category. "Probably fine" is not a category.

## Provenance chain

```text
EVENT → EVIDENCE → INTERPRETATION → DECISION → ISR / REQUIREMENT
```

Each link carries identities and hashes. `trace/1` walks the full chain;
a broken link renders as an explicit gap with what is missing, never as
an assumed continuity.

The VS1 D22–D29 record set is the reference implementation of this
pattern: observation IDs → normalized evidence → epistemic
classification (observed/inferred/unknown/contradiction) → decision
with unknowns preserved.

## Integrity

- Projections recomputed from the same event set must be semantically
  identical (determinism requirement; timestamp rendering excluded).
- Tampered evidence must fail verification loudly, not degrade into
  plausible-looking output.
- Evidence detail views show: source, type, claim, result, scope, what
  is *not* proven, and full provenance with per-link verification state.

## Secrets

Evidence ingestion redacts credential material at the boundary. If
secret-shaped material reaches the Observatory, it is not reproduced;
the occurrence is recorded as a finding and the affected evidence is
quarantined from display pending review. Fail closed where integrity is
affected.

## What the model refuses

- Upgrading `:unknown` to success because surrounding evidence is green.
- Merging contradictory sources by picking the convenient one.
- Treating test success as certification (tests establish their defined
  claims; certification is a separate governance decision).
- Presenting replayed/cached state as live without a staleness marker.
