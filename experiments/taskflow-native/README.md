# TaskFlow ESAP-Native Generation Trial

This experiment tests whether ESAP can derive and build TaskFlow from the problem specification without receiving the reference implementation.

## Authority boundary

Input allowed to the generator:

- `PROBLEM.md`: technology-neutral software problem.
- `ACCEPTANCE.json`: required capabilities, invariants, negative cases and quality gates.

Explicitly forbidden inputs:

- `golden-projects/taskflow/app/**`
- `golden-projects/taskflow/ARCHITECTURE.md`
- generated/reference source code
- technology-specific implementation hints

The reference application is an oracle for evaluation only. It is never an input to generation.

## Required ESAP sequence

1. Normalize the problem.
2. Derive an ISR and requirement graph.
3. Identify assumptions and uncertainty.
4. Select/evolve an architecture without changing the ISR.
5. Select one or more compiler backends from declared capabilities.
6. Materialize the generated application.
7. Verify structure, syntax, security, behavior and ISR traceability.
8. Run the application in an execution environment.
9. Collect runtime evidence.
10. Diagnose failures and make bounded repairs.
11. Re-verify from the original ISR.
12. Stop when required scope is certified.

## Anti-shortcut rule

A generated project is not successful merely because it resembles the reference implementation or passes copied tests. Certification requires traceability from the original specification through ISR, architecture, implementation, verification and runtime evidence.

## Current execution status

The repository has the typed IntentCompiler/ProjectCompiler path and compiler backends needed for the experiment. A genuine run requires a configured LanguageModelProvider or another ESAP-native reasoning provider; a recorded transcript is useful for deterministic regression tests but **does not count as an autonomous generation result**.

Therefore this experiment deliberately records provider availability separately instead of fabricating a result.

## Provider-free semantic preflight

Run the deterministic preflight from the repository root:

```bash
PYTHONPATH=.:experiments/taskflow-native:experiments/taskflow-native/provider_free:$PYTHONPATH python -m provider_free.run_trial
```

The runner writes a JSON report to stdout and exits non-zero while the trial is
blocked. An optional `--output PATH` also writes the report to that path. The
current expected result is `BLOCKED`: the canonical snapshot produces a
graph-bound ledger with 15 unresolved mandatory semantic fields. No
SystemModel, typed ISR, backend plan, generated application, or runtime result
is claimed.

A complete-looking ledger is not sufficient to proceed. The runner also blocks
when the ledger is structurally complete but trusted source/certificate
verification is not implemented. Do not mark caller-supplied provenance strings
or approval references as trusted evidence. This preflight is not yet the
full generation orchestrator; the live compiler path must remain behind the
same semantic and evidence gates.

## Trusted semantic-resolution envelope

The preflight can load a candidate ledger from
`TIANNARA_TASKFLOW_RESOLUTION_RECORD` and verify a reviewer-attested resolution
envelope through `provider_free.trusted_evidence`. The verifier binds the attestation to the
active requirement-graph ID/hash, the exact problem and canonical acceptance
hashes, and the serialized resolution-ledger hash. It checks an HMAC-SHA256
signature using `TIANNARA_TASKFLOW_TRUSTED_EVIDENCE_KEY`; the JSON envelope
path is supplied with `TIANNARA_TASKFLOW_EVIDENCE_ENVELOPE`.

The HMAC key is a shared secret and must be provisioned out of band. Keep it
out of the repository and unavailable to the generator/compiler process; only
the trusted reviewer workflow may use it to sign an envelope. A valid HMAC
authenticates that review attestation and its bound inputs, but is not proof
that generated code works. Missing keys, missing envelopes, tampered ledgers,
and mismatched snapshots remain blocked. Even a valid envelope does not yet
authorize generation because live ProjectCompiler orchestration and runtime
verification remain separate gates.


### Reviewer decision template (not an authorization artifact)

`provider_free/taskflow_review_decision_template.json` is a field-by-field reviewer worksheet for the 15 mandatory TaskFlow semantics. It records what the canonical problem/acceptance sources actually say and makes unspecified decisions visible as questions instead of compiler defaults.

- All 15 entries intentionally start as `UNRESOLVED`.
- `reviewer_value`, source hashes, and reviewer authorization fields are intentionally empty.
- The template is not a trusted resolution ledger, does not contain a signature, and cannot authorize generation.
- Complete it only through the trusted review process; then produce the separately authenticated evidence envelope required by `run_trial.py`.
- Do not turn an open question into an assumed default merely to make the generation gate pass.

This template improves review readiness only. Until the trusted envelope is verified and the live semantic projector/backend-consumption gates are implemented, TaskFlow generation and certification remain blocked/UNKNOWN.
