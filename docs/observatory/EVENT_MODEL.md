# Observatory Event Model

## Canonical envelope

Every material observation is normalized into one typed envelope:

```elixir
%Observatory.Event{
  id: "...",                    # stable, unique
  timestamp: ~U[...],           # observation time, not proof
  source: :cel,                 # originating subsystem
  category: :evolution,         # runtime | evolution | evidence |
                                # governance | knowledge
  type: :candidate_generated,   # domain event type
  subject_id: "EV-002",         # stable subject identity
  correlation_id: "...",        # groups related events
  causation_id: "...",          # the event that caused this one
  payload: %{...},              # domain data (no secrets)
  epistemic_status: :observed,  # observed | inferred | unknown |
                                # contradiction
  authorization: :granted,      # authority state where relevant
  evidence_refs: [...],         # evidence identifiers
  provenance: %{...},           # hashes, upstream identities
  severity: :info               # debug | info | warning | error | fatal
}
```

`id`, `timestamp`, `source`, `category`, `type`, `subject_id`, and
`epistemic_status` are mandatory. The type system must reject an event
that lacks them.

## Epistemic typing (non-negotiable)

| Status          | Meaning                                              |
|-----------------|------------------------------------------------------|
| `:observed`     | Directly recorded by an authoritative source.        |
| `:inferred`     | Follows from evidence; carries reasoning + scope.    |
| `:unknown`      | Cannot be established from available evidence.       |
| `:contradiction`| Authoritative sources disagree; both preserved.      |

Additionally, measurements distinguish absence from value:

```elixir
latency_ms: nil,
latency_status: :not_measured
```

The following are **distinct states** and must never be coerced:

```text
:unknown  ≠  :failed  ≠  :not_applicable
nil       ≠  0        ≠  false
```

Rationale, carried over from the VS1 epistemic gates: the most dangerous
Observatory failure is a green display over absent evidence. The type
system is the first line of defense.

## Stable identities

Subjects use stable IDs (`REQ-001`, `CAP-006`, `EV-002`, `RUN-001`,
`EVD-…`, `CON-001`, gate IDs) connected as:

```text
REQ → CAPABILITY → EVOLUTION → RUN → OBSERVATION → EVIDENCE → DECISION
```

`trace/1` reconstructs this chain; broken links are reported as gaps,
never papered over.

## Payload rules

- No credentials, tokens, secrets, or private material. Ever.
- No second governance implementation: payloads carry *facts and
  references*; authorization and policy live in the backend.
- Correlation/causation IDs are required for command flows so a human can
  follow request → check → decision → event.
