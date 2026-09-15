# Observatory Engineering Principle

> **The Observatory may display, correlate, explain, and request.
> It must never fabricate, silently infer, bypass governance,
> or become an unobserved source of truth.**
>
> **Every material displayed claim must be traceable to authoritative
> runtime state, evidence, or an explicitly declared epistemic state.**

This principle outranks every other document in `docs/observatory/`.
Where any spec below conflicts with it, the principle wins and the spec
must be amended.

## What this means in practice

1. **Display** — render authoritative state and evidence faithfully.
2. **Correlate** — join events, evidence, and lineage; correlation is
   mechanical (shared IDs, shared hashes), never interpretive.
3. **Explain** — reconstruct *why* from recorded evidence (`trace/1`,
   `explain/1`); explanation cites sources or states ignorance.
4. **Request** — human actions enter as governed command *requests*
   (`request_command/2`); the Observatory executes nothing itself.

## What is forbidden

- Rendering `:unknown` / `:not_measured` as `0`, `:ok`, `false`, or any
  value that implies a measured outcome.
- Converting a missing reading into a success, or a failed reading into
  silence.
- Enforcing policy, authorization, or epistemic judgment in frontend code.
- Mutating runtime, evidence, or governance state from a read path.
- Presenting a projection without a visible path back to its source events.

## Document index

- `ARCHITECTURE.md` — unified gateway over existing observation sources.
- `EVENT_MODEL.md` — canonical event envelope and epistemic typing.
- `API_CONTRACT.md` — public function contract (views, ingestion,
  subscription, commands, traceability).
- `GOVERNANCE_BOUNDARY.md` — command/request discipline and authority states.
- `EVIDENCE_MODEL.md` — evidence binding, provenance, integrity.
- `UI_SPEC.md` — screens, information levels, operational questions.
- `CODE_QUALITY.md` — backend quality rules.
- `TEST_STRATEGY.md` — layered testing through authorization and provenance.
- `DEFINITION_OF_DONE.md` — completion chain per feature.

Status: **draft for review**. Nothing here authorizes implementation.
