# Bucket 3.10 — Architecture-level NFR, security and privacy reasoning

Bucket 3.10 moves non-functional reasoning upstream into architecture and repair
candidate assessment.

## Governed constraints

The engine supports explicit constraints for:

- security
- privacy
- performance
- operability
- cost
- complexity

Each constraint declares a threshold, severity, and comparison direction.

## Evidence boundary

A candidate is admissible only when every mandatory constraint has current
measurement evidence and no mandatory constraint is violated.

Missing or stale evidence is therefore **insufficient**, not a pass.

Advisory constraints are reported separately and cannot silently override
mandatory constraints.

## Governance boundary

The assessment is read-only. It does not select a globally optimal candidate,
perform mutations, or certify the project.

Its intended role is:

candidate generation -> functional verification -> NFR/security/privacy
assessment -> regression checks -> evidence -> governed admission

This keeps architecture decisions evidence-bounded and prevents a candidate
with attractive performance or cost from silently violating mandatory security,
privacy or correctness constraints.

Runtime tests are not claimed as passed unless an external CI/runtime result
verifies them.
