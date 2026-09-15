# Observatory Backend — Design Output

Source: `folder/ob_backend.md` (backend production batch), extracted
mechanically file-by-file (27 modules, no hand copying).

## Status

- **Design output for the Tiannara track, not runtime code of this
  workspace.** Nothing here is compiled, executed, or depended upon by
  this repository. Full compilation requires the Tiannara host project
  (Phoenix/PubSub, application supervision, prior-batch modules such as
  `Event`, `Projections` core entrypoint, `Gateway` v1, `Tracer` v1,
  `Channel`, which this batch builds upon but does not include).
- All 27 files pass Elixir parse checks (`Code.string_to_quoted`).
  Compilation and tests must run in the Tiannara repository.
- Uncommitted. Integration into the Tiannara repo needs its own
  authorization there.

## Amendments applied here (with reasons)

1. **Atom safety** (`projections/evolution.ex`): `String.to_atom/1` on
   external input → `String.to_existing_atom/1` with existing
   `:unknown`/`:none` fallbacks. Unbounded atom creation exhausts the
   atom table and crashes the VM.
2. **Timestamp fabrication removed** (`events/validator.ex` + 4 typed
   constructors): `coerce_timestamp/1` returned `DateTime.utc_now()`
   for invalid input; it now returns `{:error, :invalid_timestamp}`
   and every constructor fails closed. A bad timestamp must never
   silently become *now*.

## Contents

`lib/observatory/` — events (validator, runtime/evidence/evolution/
governance constructors), projections (helpers, runtime, evolution,
evidence, knowledge, governance, facade), store, event_bus, ingestion,
query, api/*, governance, gateway, tracer, supervisor.
