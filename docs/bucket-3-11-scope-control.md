# Bucket 3.11 — Autonomous scope control

Bucket 3.11 establishes a hard boundary between governed work and invented
work.

## Scope classes

Proposals are classified as:

- **required** — directly traced to an authoritative obligation or explicitly
  authorized by the human authority.
- **necessary_support** — work needed to support a governed obligation.
- **advisory** — useful but not required; it is not executable.
- **rejected** — no valid governed scope, or an unknown scope reference.

Unknown obligation references fail closed.

## Anti-hallucination rule

A proposal cannot become required merely because an implementation agent thinks
it would be useful. Requirements must trace to governed obligations, or receive
explicit authorization.

Advisory discoveries remain advisory and cannot silently mutate project scope.

## Completion boundary

This module is intentionally read-only. It does not execute mutations,
certify work, or decide technical implementation. It supplies a governance
decision to the execution layer.

The intended lifecycle is:

authoritative scope -> necessary supporting work -> implementation ->
verification -> certification -> completion/stop

After completion, an advisory idea remains an advisory idea until explicitly
promoted through governance.

Runtime tests are not claimed as passed unless an external CI/runtime result
verifies them.
