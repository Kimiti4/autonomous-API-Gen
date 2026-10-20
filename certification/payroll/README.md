# Payroll behavioral certification gate

The payroll certifier is an evidence gate, not a payroll calculation engine. It
returns `CERTIFIED` only when one exact generated-candidate SHA-256 is bound to
all required source, statutory, independent-oracle, frontend, backend-runtime,
and ledger-chain evidence. Missing evidence is a finding, never a default pass.

## Required evidence

- Every mandatory reviewed TOR requirement is represented by an ISR
  `requirement_ref`.
- The lowered plan contains typed data fields, business rules, state
  transitions, API contracts, explicit authorization policies, effect
  contracts, invariants, and typed event contracts.
- Every selected backend declares and passes the semantic capability gate for
  the exact plan. A backend that cannot implement a feature blocks release.
- Each statutory scheme required by the reviewed TOR has official source
  provenance, source SHA-256, reviewer approval, effective-dated coverage of
  the payroll period, and passing test vectors.
- Each required independent oracle category is bound to a source requirement,
  an independently authored test set, and the exact candidate hash.
- Frontend production build, generated unit tests, and browser E2E pass with
  hashed logs and artifact identity.
- Every required backend has complete runtime trials, independent verification,
  health and cleanup evidence, and a valid evidence-ledger chain.

## No fabricated statutory rules

This module contains no PAYE, NSSF, SHIF, pension, housing levy, or other
statutory rates. The reviewed TOR determines which schemes are required; current
official sources and their effective dates supply the actual values. Where a
payroll period spans a statutory change, evidence must cover the entire period
without gaps or conflicting overlapping intervals.

## Current interpretation

Structural backend certification is not payroll certification. A payroll plan
that lacks any required behavior, statutory source, independent oracle, live
frontend evidence, or backend runtime proof remains `NOT_CERTIFIED`. The
report is designed to make the missing evidence explicit so the general
compiler capability can be completed rather than bypassed with a payroll-only
special case.
