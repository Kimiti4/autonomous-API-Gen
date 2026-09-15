# Observatory Code Quality

Mandatory for all Observatory backend code.

## Public functions

- `@spec` + `@doc` on every public function.
- Document failure modes in the spec (`:unavailable`, `:timeout`,
  `:invalid_response`, `:process_crashed`), not just success shapes.

## Size and structure

- No giant builders. Split `build_dashboard/0`-style aggregators into
  `build_overview/0`, `build_runtime/0`, `build_evolution/0`,
  `build_governance/0`, `build_knowledge/0`, … — one per concern.
- Pure derivation (`derive_evolution_status/1`, `build_timeline/1`)
  takes events in, state out: no database, no messaging, no mutation.

## Errors

- Broad `catch _, _ -> default` is allowed **only** as an explicitly
  bounded containment mechanism with a logged reason. It must never be
  the normal error path, and it must never silently produce `%{}` or
  `0` where `:unavailable` belongs.
- Distinguish failure kinds (`:unavailable`, `:timeout`,
  `:invalid_response`, `:process_crashed`) and expose them to the UI.

## Atom safety (mandatory)

- Never call `String.to_atom/1` on external input (events, payloads,
  params, topic segments). Unbounded atom creation exhausts the atom
  table and crashes the VM. Use `String.to_existing_atom/1` with an
  explicit `:unknown`/`:none` fallback — the rescue clause is part of
  the contract, not an afterthought.

## Timestamp hygiene (mandatory)

- Never substitute `DateTime.utc_now()` for an invalid timestamp.
  Coercion returns `{:ok, ts} | {:error, :invalid_timestamp}` and every
  constructor fails closed. A bad timestamp silently stamped *now* is
  fabricated provenance.

## Side effects

- Read functions (`dashboard/0`, `trace/1`, `explain/1`, …) change
  nothing: no state, no evolution trigger, no repair, no process start,
  no evidence write. Test this property directly.

## Determinism

- Same event set → same semantic projection. Test with reordered input
  and timestamp-rendering variations; tampered input must fail loudly.

## Frontend

- Typed API client against `API_CONTRACT.md`; lint + component tests.
- Zero duplicated governance/epistemic logic outside the backend.

## CI quality gate (Observatory-specific)

```text
format · compile --warnings-as-errors · static analysis
unit · property/invariant · integration · API contract
WebSocket/event · authorization · provenance · tamper · failure-path
frontend type/lint · frontend component tests · E2E
no secrets · no mock data in production paths
no unauthorized mutation · no fabricated metrics
no silent unknown→success conversion
```

And: **green tests ≠ certification.** Tests establish defined claims;
certification stays a separate governance decision — same rule as D29.
