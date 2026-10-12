# Comparative Application-Compiler Evaluation Protocol

Status: **PROPOSED / NOT EXECUTED**

This protocol applies to TaskFlow first and then every remaining application-generation benchmark whose canonical specification and acceptance criteria are available. It does not authorize generation while the semantic-resolution, trusted-evidence, or downstream-consumption gates are blocked.

## Experimental design

For each application, execute exactly two primary iterations:

- **Iteration A:** compile the canonical, frozen input with compiler implementation A.
- **Iteration B:** compile the same canonical, frozen input with a materially different compiler implementation B.

The compiler identities must be recorded by implementation name/version and source revision. Merely changing configuration, model temperature, or backend target does not count as a different compiler unless the compilation algorithm/path itself is demonstrably different. If two independent compiler paths are not yet available, record the application as **BLOCKED — second compiler unavailable**; do not label a repeated run as a comparison.

### Fairness and isolation controls

Before compiler qualification, run the fail-closed declaration checker at `experiments/compiler-benchmarks/taskflow_input_parity.py` against a proposed shared-input manifest. It must cover all 15 mandatory TaskFlow fields and reject unresolved fields, missing canonical hashes, differing semantic-value digests, duplicate implementation identities, or missing downstream-consumer bindings. A successful preflight means only that declarations are internally consistent; it is **not** evidence that digests are authentic, fields are actually consumed, or the compilers are qualified. Those claims require trusted review and independent source/runtime evidence.

1. Freeze and hash the canonical problem statement, acceptance criteria, assets, and any reviewed semantic ledger before either iteration.
2. Both compilers receive semantically equivalent inputs and the same allowed tools, dependency/network policy, resource budget, timeout, and environment constraints.
3. Use separate clean workspaces, output directories, databases, credentials, and runtime instances. No artifact, generated code, state, or hidden cache may leak from A to B or vice versa.
4. Record the compiler order. Prefer alternating or predeclaring order across applications to reduce order and infrastructure bias.
5. Do not silently repair one output more than the other. Any human intervention must be logged, timed, classified, and reported separately; the untouched generated result remains the primary result.
6. The acceptance evaluator must be independent of either compiler and must use the same versioned test suite for both outputs.
7. Run the same verification sequence against both artifacts. A test not run is **UNKNOWN**, not PASS. Simulation, mocked evidence, and self-reported compiler claims cannot establish live runtime behavior.
8. Keep generation authorization separate from evaluation. A successful build or benchmark result does not bypass trusted review or authorize promotion/listing.

## Required per-iteration evidence

Capture at minimum:

- Application ID, iteration ID, compiler name/version/source revision, and compiler configuration.
- Canonical input hashes and semantic-ledger/envelope references (without exposing secrets).
- Start/end timestamps, elapsed time, exit status, resource use where available, and all human interventions.
- Generated artifact manifest and hashes; dependency lockfiles; build logs; test reports.
- API contract and behavior tests, frontend interaction/state-transition tests where applicable, persistence and migration checks, authentication/authorization and negative-case tests, runtime health/readiness, and operational/recovery checks.
- Requirement-to-artifact-to-test traceability, including unsupported or unrepresented semantics.
- Failures, skipped checks, unknowns, deviations, and reproducible instructions.

Do not store signing keys, tokens, passwords, or other secrets in benchmark reports or generated artifacts.

## Scoring and comparison

Report raw evidence before any aggregate score. Compare the two iterations on:

- Acceptance-criteria coverage and independently verified correctness.
- Security and authorization failures, including negative cases.
- Data integrity, consistency, idempotency, and recovery behavior.
- API correctness and frontend behavior.
- Build reproducibility, dependency health, and runtime stability.
- Traceability and evidence completeness.
- Generation time, repair/intervention time, and resource consumption.

A critical security or data-integrity failure must not be hidden by a high aggregate score. Report both per-criterion outcomes and an overall status:

- **PASS:** all required gates for the stated scope have independently verified evidence.
- **FAIL:** a required gate was run and failed.
- **UNKNOWN:** evidence is absent, incomplete, simulated where live proof is required, or not independently verifiable.
- **BLOCKED:** a prerequisite prevents a fair or safe trial from starting.

If both runs fail, the comparison is still useful but neither application is accepted. If one run wins, the result applies only to the frozen benchmark and recorded environment; it is not proof of universal compiler superiority.

## Execution order

1. **TaskFlow:** finish trusted semantic review, typed projection, and proof that downstream planning/backend generation consumes every required semantic. Until then, record generation as BLOCKED and do not create a misleading A/B result from an unsafe partial path.
2. **Compiler-path qualification:** identify two genuinely distinct compiler implementations and demonstrate each can be invoked independently with versioned inputs and evidence.
3. **TaskFlow A/B trial:** run both isolated iterations against the same canonical TaskFlow specification and acceptance suite.
4. **Remaining applications:** enumerate only applications with canonical specifications and acceptance criteria already present in the repository. Freeze each application's inputs and use the same two-iteration protocol. If an application lacks an acceptance suite or its semantics are unresolved, mark it BLOCKED until that gap is addressed.
5. **ReadingShelf:** remains deferred until TaskFlow's execution and evidence boundaries are sound; then apply the same protocol rather than giving it a weaker evaluation.
6. **Publish results:** commit machine-readable run manifests and evidence summaries. Keep raw artifacts separate per application/compiler/iteration. Do not claim certification from benchmark completion alone.

## Result layout

Use a structure equivalent to:

```text
benchmark-results/
  <application-id>/
    input-manifest.json
    compiler-a/
      run-manifest.json
      artifacts/
      evidence/
    compiler-b/
      run-manifest.json
      artifacts/
      evidence/
    comparison.json
    report.md
```

The result layout is a target contract, not a claim that runs or artifacts already exist.
