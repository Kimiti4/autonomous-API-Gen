# TaskFlow Generalization and Blind-Input Review

**Review date:** 2026-10-10  
**Base commit reviewed:** `de7547a6ce60934a869253d5a641456f3c38ccc8`  
**Related work:** [PR #72](https://github.com/Kimiti4/autonomous-API-Gen/pull/72) merged fixture-scoped trial foundation; [PR #73](https://github.com/Kimiti4/autonomous-API-Gen/pull/73) contains a draft fail-closed integrity gate.  
**Certification policy:** a green build or generated artifact is not proof of independent generation if task-specific answers are embedded, forbidden implementation inputs are readable, or the acceptance scope differs from the specification.

## Findings

| Requirement | Result | Evidence |
|---|---|---|
| Reconcile the trial against current `main` | **FAIL — unresolved integration** | PR #72 is merged at `de7547a6ce60934a869253d5a641456f3c38ccc8`. PR #73 remains a draft based on the earlier `cbe0a004055bb28fb6938a8b833075c035a45e5e`, so its changes/checks have not been reconciled into the current base. |
| Remove task-specific fixture answers | **FAIL** | `experiments/taskflow-native/run_trial.py` defines literal `ELICITATION` and `EXTRACTION` payloads and `seed_transcript()` writes those payloads into a recorded transcript. `RecordedModelProvider` replays a matching recorded payload and deliberately fails on unrecorded calls; it does not independently interpret the specification. |
| Verify the trial is testing the stated problem | **FAIL** | `experiments/taskflow-native/PROBLEM.md` describes a multi-user team system with registration, workspace tenancy, owner/manager/member RBAC, projects, task assignment, comments, audit history, search/filter, dashboard, and session revocation. The runner's hardcoded extraction instead describes a single installation, shared access key, tasks, and named lists. These scopes do not match. |
| Enforce a technical blind-input boundary | **FAIL** | The draft `check_generalization_integrity.py` reports the trial workspace's forbidden golden implementation/architecture and repository metadata as blockers. Hash pins detect changed inputs; they do not prevent the generator from reading other files. The runner executes in a checkout containing those paths. |
| Second distinct specification defined and exercised | **UNKNOWN / NOT DEMONSTRATED** | The draft contract has no `generalization_specs` entry; no evidence was found for a second specification being independently compiled and generated. |
| Generated application passes frontend, backend/API, build, runtime, regression checks for an unseen specification | **UNKNOWN / NOT DEMONSTRATED** | Existing trial harness evidence is scoped to the current fixture-driven TaskFlow path. No qualifying second-specification run with independently derived requirements and an enforced read boundary was identified. |
| Unsupported capabilities explicitly marked unverified | **UNKNOWN / NOT DEMONSTRATED** | The trial cannot claim capability coverage for the multi-user problem from the simpler hardcoded requirement graph. Each required capability must be linked to generated implementation and real verification evidence before any PASS. |

## Why this is a hard stop

The issue is not just that a second test case is missing. The first trial's hardcoded requirement answers omit essential security and tenancy requirements from the problem specification. A build or smoke test for the resulting simpler application would not certify the stated TaskFlow application.

The draft integrity checker is correctly conservative in principle: it blocks rather than turning these limitations into a PASS. Its current failing workflow is a useful detection signal, not a successful generation certification. Do not merge or waive the failing gate simply to make CI green.

## Required sequence to close

1. Rebase/reconcile the draft integrity work against current `main` and keep its blockers executable.
2. Replace embedded `ELICITATION`/`EXTRACTION` outputs with an actual configured `LanguageModelProvider` implementation. A missing/unreachable provider must return BLOCKED/UNKNOWN, never synthesize a fixture answer.
3. Run generation in a restricted workspace/container that exposes only the chosen specification, its acceptance contract, compiler/runtime code, and explicitly permitted dependencies. Do not mount the golden implementation, architecture notes, or repository metadata into the generation process.
4. Add a second materially distinct specification with its own acceptance contract; keep its expected implementation outside the generator's read boundary.
5. Execute the generator on both specifications from clean isolated workspaces and preserve input hashes, provider/model identity, call transcript hashes, requirement graph/ISR hashes, generated file manifest, and verification outputs.
6. For the second app, run frontend tests/build, backend/API unit and integration/contract tests, full build, real runtime smoke/E2E checks, and regression suite. Re-derive evidence independently from the files actually produced.
7. Report each capability PASS only with matching real evidence; unsupported or unevaluated capabilities remain UNKNOWN/UNVERIFIED. Never count simulated evidence as runtime certification.

## Current verdict

**Independent natural-language generation: NOT CERTIFIED.**  
**Second-specification generation: UNKNOWN / NOT RUN with qualifying isolation.**  
**Full-stack certification for a genuinely unseen specification: UNKNOWN.**

This review records findings and does not claim a successful second generation or deployment.
