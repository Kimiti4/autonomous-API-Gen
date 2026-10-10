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
