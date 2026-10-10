# TaskFlow Generalization and Blind-Input Review

**Review date:** 2026-10-10  
**Main evidence baseline:** `5410e077ca836e22b0b41b94870d035551b6e48d`  
**Related work:** [PR #72](https://github.com/Kimiti4/autonomous-API-Gen/pull/72) is merged. [PR #73](https://github.com/Kimiti4/autonomous-API-Gen/pull/73) remains a draft and is not mergeable against current main.  
**Certification rule:** a green lint/test workflow, generated files, or an archived artifact does not establish independent generation if the task statement, acceptance scope, or read boundary is wrong.

## Evidence matrix

| Requirement | Status | Evidence and boundary |
|---|---|---|
| Reconcile the generation trial with the canonical main specification | **FAIL — unresolved** | Current main's `experiments/taskflow-native/PROBLEM.md` specifies a multi-user team application with workspace tenancy, RBAC, projects, comments, audit history, search/filter, dashboard, and revocable sessions. PR #73 replaces it with a much smaller single-installation task/list app. PR #73 also uses a different acceptance schema focused on ten CRUD checks. These are not equivalent scopes and must not be merged as if they were the same trial. |
| Remove task-specific fixture answers | **PASS — source-level check only** | The current PR #73 runner uses `OllamaModelProvider` plus `RecordingModelProvider` to record live structured model output. The integrity check reported `independent-interpretation: PASS` on run [38058999127](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38058999127). This proves the literal ELICITATION/EXTRACTION fixture payloads are absent from that runner; it does not prove successful generation. |
| Enforce blind-input boundary | **PASS — trial workspace check** | Workflow step removes `.git`, the golden application, and its architecture document before generation; the integrity check reported `enforced-blind-input-boundary: PASS` on run [38058999127](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38058999127). The boundary must be preserved in the reconciled workflow. |
| First live generation attempt | **FAIL — blocked before artifact generation** | Run [38058999127](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38058999127) failed with `LanguageModelError` during live intent compilation. The evidence evaluator then failed because graph, factory, manifest, runtime, and result evidence files were absent. This is not a generated-app failure after build; generation did not reach those stages. |
| Longer-timeout retry | **UNKNOWN — pending at review time** | The runner/workflow timeout was increased from 180 to 600 seconds after the initial run. The retry [38059475531](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/38059475531) was in progress at the last observation. Do not count it as a pass until its final result and artifacts are inspected. |
| Second distinct specification generated and verified | **UNKNOWN / NOT DEMONSTRATED** | `ReadingShelf.md` exists as a candidate second specification, but the current contract has no `generalization_specs` entry and the workflow does not run a second generation. There is no qualifying second-spec evidence file. |
| Frontend, backend/API, build, runtime, and regression checks for a valid unseen specification | **UNKNOWN / NOT DEMONSTRATED** | The failed run did not create the evidence required by the evaluator. The hardcoded trial acceptance flow also assumes `tasks` and `task_lists`, so it cannot honestly certify ReadingShelf without a separate, independently specified test profile. |
| Unsupported capabilities explicitly marked unverified | **REQUIRED** | Until the canonical TaskFlow capability set is mapped to generated artifacts and real verification, workspace tenancy, RBAC, projects, comments, activity history, search/filter, dashboard, audit trail, and session revocation remain unverified by this trial. |

## Required reconciliation sequence

1. Keep the current main TaskFlow problem statement and its acceptance contract authoritative; do not replace them with the smaller CRUD fixture to obtain a green run.
2. Rebase/reconcile PR #73's compiler and integrity changes without overwriting the canonical problem/acceptance scope. PR #73 is currently dirty/unmergeable and must not be merged as-is.
3. Keep the workspace isolation step executable and fail closed if forbidden golden implementation or repository metadata is present.
4. Make live model failure diagnosable by preserving safe, classified error evidence. Do not fall back to canned task-specific answers.
5. Add a second-spec run record only after ReadingShelf has been independently generated and its own API/frontend/build/runtime/regression checks have executed. Its expected implementation must remain unavailable to the generator.
6. Preserve per-capability traceability. A generated artifact, static build, or green general-purpose CI is not a substitute for capability-specific evidence.

## Disposition

**Generalization is not certified.** The blind-input boundary and absence of embedded answer fixtures pass their narrow checks, but the current PR's problem/acceptance scope diverges from main, the first live generation attempt was blocked, and the second specification has not been run. Staging/production behavior is outside this CI evidence.
