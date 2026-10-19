# Behavioral ISR Contract v1

## Purpose

The canonical ISR has a typed graph, requirement references, events, security
policy nodes, effects, invariants, consequences, and immutable content-addressed
revisions. However, graph node properties are generic mappings, and the current
compiler plan lowers mostly names and graph edges. That is not enough to claim
that a generated application implements business behavior.

This contract adds typed, technology-neutral semantic payloads carried in a
node's properties under the key behavior. The payload participates in the
existing canonical graph hash because node properties already participate in
content hashing. No second source of truth or hash algorithm is introduced.

## Supported semantic payloads

| Owning node type | Contract | Meaning |
|---|---|---|
| data_model | DataModelBehavior | Typed fields, requiredness/nullability, decimal/money precision, constraints, and invariants |
| service | ServiceBehavior | Business rules and named state transitions |
| api | ApiBehavior | Method/path, request/response field contracts, and required policy IDs |
| effect | EffectBehavior | Effect kind and explicit idempotency semantics |
| security_policy | SecurityBehavior | Declared roles and explicit allow/deny rules; empty rules never mean allow |

Expressions are bounded ASTs, not executable source. Supported operators are
arithmetic, comparisons, boolean composition, conditional selection, literals,
and field references. There is no eval, arbitrary function call, or backend
technology name in the contract.

## Compatibility and safety

- Existing structural ISR revisions without a behavior payload remain valid and
  retain their current canonical hash.
- Once a node supplies a behavior payload, it must validate against the schema
  for that node type; unknown fields and unsupported owner types fail closed.
- Expression field references and API authorization-policy references are
  checked across the graph at revision construction.
- A valid behavioral payload is not proof that an emitter consumes it. Until
  lowering and target emitters are integrated and independently tested, it
  must not be reported as behaviorally implemented or certified.
- No payroll-specific semantics or statutory rates are embedded in this schema.
  Payroll uses the same typed fields, expression tree, rules, effects, and
  authorization contracts as other domains.

## Required next gates

1. Validate behavior payloads at canonical ISR revision construction.
2. Validate field uniqueness, expression field bindings, referenced policy IDs,
   and cross-node links.
3. Lower typed semantics into the technology-neutral compilation plan without
   lossy projection.
4. Require each backend to declare and prove support for each semantic feature.
5. Independently test generated behavior against requirement-derived oracles.
6. Keep legacy structural-only candidates eligible only for structural
   certification; behavioral claims require explicit behavioral completeness.

This change defines and validates a schema boundary. It does not claim that
payroll calculations, statutory compliance, frontend generation, or behavioral
certification are already implemented.
