# Bucket 4.1 — Existing-codebase audit bundle

`audit_existing_codebase` composes the existing evidence-first repository
layers without mutating source:

- deterministic code-risk scanning;
- structural/import analysis;
- complete-inventory gating;
- dependency impact analysis;
- bounded root-cause hypotheses;
- repair candidates with explicit verification paths;
- deterministic evidence digest.

A scanner or structural finding is not itself an authoritative requirement.
Only the governed scope/ISR can authorize executable work. Partial inventory
cannot support a full-audit or repair-certification claim.

This bundle is intentionally read-only. Mutation, verification, certification,
and deployment remain separate governed stages.
