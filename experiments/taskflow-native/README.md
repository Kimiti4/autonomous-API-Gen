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
