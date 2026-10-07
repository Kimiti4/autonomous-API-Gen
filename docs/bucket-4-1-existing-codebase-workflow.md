# Bucket 4.1 — Existing-codebase maintenance and improvement

Bucket 4.1 governs work against an existing repository without treating scanner
findings as requirements.

## Controlled lifecycle

1. Intake the human/ISR-authorized objective.
2. Establish a complete repository inventory and scan scope.
3. Scan deterministically without executing source.
4. Diagnose findings and keep hypotheses separate from facts.
5. Perform dependency/architectural impact analysis.
6. Generate and evaluate repair candidates.
7. Apply changes only through the existing governed mutation path.
8. Run targeted and regression verification, then E2E verification.
9. Certify only with fresh authoritative evidence.
10. Produce documentation/deployment readiness evidence.
11. Stop when the authorized obligations are complete; additional findings are advisory.

## Scope and anti-hallucination controls

- A partial inventory cannot support a full-audit claim.
- Scanner findings do not create authoritative requirements.
- Advisory observations cannot expand executable scope.
- Surface-only modes are explicit: frontend, backend, and API-contract.
- Production deployment remains subject to the existing human-authorization boundary.
- The workflow is a contract; it does not mutate repositories itself.

The existing repository impact, root-cause, repair, verification, completion, and
deployed-app modules remain the execution/evidence layers. This module only
provides the Bucket 4.1 lifecycle admission boundary.
