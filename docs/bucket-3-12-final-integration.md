# Bucket 3.12 — Final Bucket 3 integration and closure

Bucket 3.12 establishes the final decision boundary across the governance
layers introduced in Bucket 3.

## Change admission

A proposed change can reach **ADMIT** only when all of these are true:

1. scope control says the work is executable;
2. mutation impact is bounded;
3. cross-layer consistency is clean;
4. mandatory NFR/security/privacy constraints are admissible;
5. the project is not already complete.

Any failed gate produces **REJECT**.

## Completion

A project whose governed obligations are all certified reaches **STOP**.

Completion is a hard boundary. A new idea cannot bypass it merely because the
scope proposal is marked explicitly authorized. A new governed obligation must
be established/reopened first, preserving the historical certification.

## Governance boundary

The integration engine is an orchestrator, not an executor. It:

- does not mutate source code;
- does not create requirements;
- does not certify evidence;
- does not declare an architecture globally optimal;
- does not turn advisory discoveries into requirements.

It only combines independently produced governance decisions into a
deterministic admission/stop/reject result.

## Bucket 3 closure

The resulting control chain is:

**governed scope → mutation impact → cross-layer consistency → NFR/security/privacy
admission → implementation/verification → governed completion → STOP**

Project memory remains append-only and epistemically separated, so the
integration layer does not silently rewrite historical project truth.

Runtime tests are not claimed as passed unless an actual CI/runtime result
verifies them.
