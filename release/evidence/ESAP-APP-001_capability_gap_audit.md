ESAP-APP-001 Capability-Gap Audit — Android End-to-End (Post-Hardening Foundation)

Baseline from hardening checkpoint (Nov 02 2026):
- W03 verified: durable adapter (`compiler/core/ledger.py`), ClickHouse authorization hardened (`test_clickhouse_hardening.py` 3/3)
- W14 remains IN_PROGRESS: frontend targets fail closed on unsupported authorization declarations; generated authorization execution is not verified
- W02/W06 IN_PROGRESS: effect contract (12 pass), full executable semantics still open
- W12 IN_PROGRESS: #166→#170 preservation complete, not verified executable
- W13 IN_PROGRESS: #171-#176 merged, not certified by merge count
- Existing compiler backends: python-fastapi (runnable CRUD + auth + TestClient); clickhouse_telemetry (analytical, `production_ready=False`)

1. Existing capability (honest):
- `PythonFastAPIBackend` can emit a complete runnable Python/FastAPI application (routes, Pydantic, auth, Kubernetes/CI manifests, real TestClient).
- `ClickHouseTelemetryBackend` can emit SQL schema + telemetry pipeline (not an app runtime).
- W13/W14 frontend compilers (React/Vue/Svelte/Angular/Next/Nuxt/LiveView/Scenic/Hologram) emit compiler targets + Playwright artifacts — not executable APKs.
- None generate Android/Gradle/APK artifacts.

2. Execution integrity (honest):
- Durable ledger (`ledger.py`) defines chain-linked evidence records; rejected attempts produce no entry (negative control preserved).
- `verify_effect_execution` binds to complete contracts only; partial contracts fail at model creation (all-or-nothing validator), not at simulated execution.
- FastAPI backend integrates `verify_executable_effect_contract`; authorization enforced (`assert_authorization_enforceable`).
- Actual emitted-filter / filter-expression negative control preserved (raises if expression drifted).
- Nothing here proves an Android APK executes; execution evidence is in-process (Python) and compiler-output (frontend fixtures), not device-level.

W14 evidence reconciliation: `tests/cbc1/test_w14_authorization_hardening.py` exercises nine frontend targets against three unsupported authorization models and verifies refusal. It also verifies required bundle files for LiveView, Scenic, and Hologram, and that those targets do not claim DEPLOY. These are compile-time fail-closed and structural checks only. They do not test a generated authorization runtime, principal/session handling, policy evaluation, or an allowed/denied operation against a running application. W14 therefore remains IN_PROGRESS.

3. Missing infrastructure (explicitly unsupported; no fabrication):
- A manual GitHub Actions workflow now provisions JDK, Android SDK and Gradle and attempts a debug APK build; it has not yet been manually dispatched against an authoritative benchmark model. Therefore no successful APK build is evidenced.
- The workflow now defines an Android Emulator API 35 launch/UI-observation step, but no emulator execution result is evidenced. Device-farm coverage is not present.
- Debug APK packaging and ZIP/manifest/DEX inspection are scripted in the workflow, but no APK artifact is evidenced. Release signing, signing-key custody and release-build verification remain unimplemented/unverified.
- Device-level authentication (Android KeyChain / Biometric / OAuth2 mobile) not implemented.
- Persistent mobile storage (SQLite / Room / DataStore / encrypted file) not bound to effect contracts.
- Cross-device synchronization (realtime sync, conflict resolution) not represented in ISR behavior.
- A basic UI Automator hierarchy dump and title assertion are scripted in the workflow, but no run evidence exists. There is no substantive native interaction suite (for example Espresso/Appium flows); Playwright artifacts cover web, not Android native.

Compiler-lineage gap confirmed during source inspection:
- The Android emitter currently accepts `tiannara.domain.models.system_model.SystemModel` directly. It does not consume the technology-neutral `compiler.core.plan.CompilationPlan` produced by `compiler.core.lowering.isr_to_plan`.
- The `CompilationPlan` carries typed services, data models, events, security policies, API operations, effects, explicit effect bindings, consequences, invariants, and frontend routes/interactions. The current Android backend only renders names from `SystemModel.data_models` into a static Compose catalogue.
- Therefore, the present Android workflow does not yet demonstrate ISRRevision → CompilationPlan → Android emitter traceability, nor preservation/enforcement of those plan semantics. A non-empty `requirements_ref.graph_id` and `graph_hash` alone do not prove the referenced graph exists, matches the model, or was used to derive the candidate.
- Required remediation: bind the Android candidate to an authoritative ISR revision/content hash, lower that revision through the canonical lowering path, validate required semantic features against an explicit Android capability declaration, and retain the plan hash plus source-to-output mapping. Reject unsupported plan semantics before emission. Do not claim the current `SystemModel` shell meets this gate.

4. Remediation — reusable vs Android-specific:
- Reusable ESAP fixes: effect-contract verification (`effect_verification.py`), authorization enforcement (`authorization.py`), durable ledger adapter (`ledger.py`), fail-closed negative controls. These apply to any backend, including Android.
- Android-specific: Gradle build profile, APK emission, emulator execution, mobile auth, persistent storage adapter, native UI automation. These require new backend/compiler targets or adapter ports, not just ESAP fixes.

5. Acceptance evidence (required before expansion):
- Requirement-to-source: a documented `CompilationPlan` + emitted bundle + source file list.
- Source-to-test: exact `toHaveText` assertions; fail-closed tests for authorization; no fabricated clients/forms/routes.
- Test-to-runtime: an APK that installs and launches; behavior observed on emulator or device (not simulated).
- Runtime-to-evidence: durable ledger record of the executed effect; chain-linked hash; negative control verifying rejected attempts leave no entry.
- Change-request verification: a subsequent change must modify the plan, re-compile, re-test (same exact assertions), and re-run (APK rebuild + emulator run) without breaking authorization / effect contracts.
- If any gate above is unsupported, capability remains unsupported — never collapsed to "supported" by aggregate passes.

Status preservation (hard constraint from W02/W06/W12/W13):
- W02/W06: IN_PROGRESS (not certified by module tests alone)
- W12: IN_PROGRESS (preservation work, not executable verification)
- W13: IN_PROGRESS (merge count ≠ certification)
- W03: verified (durable adapter + ClickHouse)
- W14: IN_PROGRESS (frontend fixtures prove fail-closed refusal of unsupported RBAC/ABAC/policy-based declarations; they do not prove generated authorization execution or runtime enforcement).
- ESAP-APP-001: audit-only at this stage; first benchmark = smallest Android end-to-end with real APK execution on emulator; no portfolio expansion until benchmark passes.

File references inspected on the remediation branch (some audit/evidence files may be branch-specific):
- `release/evidence/milestone_status_post_hardening.md`
- `compiler/core/ledger.py`
- `tests/cbc1/test_clickhouse_hardening.py`
- `tests/cbc1/test_fastapi_hardening.py`
- `tests/cbc1/test_w14_authorization_hardening.py`
- `compiler/core/effect_verification.py`
- `compiler/core/authorization.py`

5.1 Canonical-pipeline boundary reconciliation (verified on this branch):
- There are two distinct compiler contracts in the repository. The campaign compiler uses `isr.core.revision.ISRRevision` → `compiler.core.lowering.isr_to_plan` → `compiler.core.plan.CompilationPlan` → the `compiler.core.protocol.CompilerBackend` protocol (`compile`, `conformance`, `element_paths`, `test_spec`). The campaign plan builder and runner use this path.
- The Android implementation is registered in the separate `tiannara.application.compiler.CompilerRegistry`. Its `generate` method accepts `tiannara.domain.models.system_model.SystemModel` directly and returns the Tiannara `CompilationResult`; it does not implement the `compiler.core.protocol.CompilerBackend` contract.
- The repository also has a constitutional intent path: `IntentCompiler` → `project_intent_to_constitutional_isr` → `ConstitutionalSourceBinding` verification → `Constitutional CompilerPipeline`. This path uses `constitutional_architecture.isr.model.isr.ISR`, not the campaign path's `isr.core.revision.ISRRevision`. It is not evidence that the Android backend is fed by either path.
- Consequently, the phrase “canonical ISRRevision → CompilationPlan → Android emitter” must be treated as the target integration contract, not as an already wired runtime path. A bridge between the constitutional ISR and campaign ISRRevision is not established by the files inspected. Do not serialize one representation into the other or infer semantic equivalence by matching IDs/names.
- The current Android workflow validates a serialized `SystemModel` and invokes `AndroidBackend.generate(model)`. The fixture test's `graph_id="fixture"` and `graph_hash="fixture-sha256"` are test placeholders, not authoritative benchmark provenance. The workflow's non-empty graph identity/hash check is therefore only a weak shape check, not source binding.
- Required next implementation decision: select one authoritative compiler spine for this Android benchmark. Prefer the campaign spine if it is the designated ESAP backend contract: create/obtain an authoritative `ISRRevision`, lower with `isr_to_plan`, implement Android as a `CompilerBackend`, and gate it with `required_features/assert_plan_supported`. If the constitutional intent path is the source authority, specify and test a loss-aware, independently verified adapter into the campaign ISR model before compiling. In either case, bind exact source bytes, graph identity/hash, revision content hash, plan hash, and generated-file provenance; reject unrepresentable semantics before emission.
- No authoritative ESAP-APP-001 source artifact or reviewed requirement graph was found in the searches performed for this checkpoint. No benchmark requirements model has been created or substituted. The benchmark remains BLOCKED pending an identified source artifact and approved graph.

5.2 Benchmark-source discovery and scope separation (verified on this branch):
- A canonical TaskFlow source pair does exist in the repository: `experiments/taskflow-native/PROBLEM.md` and `golden-projects/taskflow/ACCEPTANCE.json`. Their contents define a full-stack task-management web application and explicit security, operational and acceptance requirements. They are valid TaskFlow inputs; they are not labelled ESAP-APP-001.
- The TaskFlow problem explicitly lists “native mobile applications” as a non-goal. Therefore TaskFlow must not be repurposed as the Android benchmark or used to justify an Android requirements graph. Its separate benchmark status remains governed by the TaskFlow parity/compiler qualification gates.
- The repository's `experiments/compiler-benchmarks/benchmark_manifest.template.json` and `coherence_suite.v1.json` identify TaskFlow and other application domains, but do not identify an ESAP-APP-001 Android source artifact. The coherence suite itself is marked SPECIFIED_NOT_EXECUTED.
- This corrects the scope of the earlier source-discovery statement: the search did not establish that the repository lacks all canonical application specs; it established that the inspected ESAP-APP-001/Android target has no identified canonical spec. TaskFlow is a separate, concrete source-backed benchmark and cannot be substituted without an explicit benchmark-scope decision.
- The next Android-specific prerequisite remains locating the actual approved Android benchmark problem statement and acceptance criteria (or receiving explicit authorization to define/freeze them). Do not derive a grocery/catalogue app from TaskFlow, a fixture, or the Android backend's current static model shell.

5.3 Android campaign-backend and benchmark-authority reconciliation (2026-11-03):
- PR #201 now adds a campaign-protocol Android backend (compiler/backends/android.py) alongside the older tiannara.application.compiler.AndroidBackend. The campaign implementation lowers an ISRRevision through isr_to_plan, compiles a deliberately static Android shell, and refuses runtime-bearing plan features it does not implement. The two Android backends remain distinct; the existence of the campaign backend does not make the older SystemModel backend equivalent or source-bound.
- The cloud workflow was updated to check out an exact source revision, validate source-spec and ISR-revision file hashes against a pinned derivation manifest, parse the revision, regenerate the candidate through the campaign backend, and bind build/emulator evidence to that candidate. The manifest hash is a pinned assertion supplied at dispatch, not a cryptographic reviewer signature or proof that the ISR faithfully represents the source specification.
- Workflow runner configuration now explicitly requests Gradle 8.9, JDK 17 and Android API/build-tools 35. It also rejects repository paths that escape the checkout, including through symlinks.
- GitHub Actions run 41631726532 for commit aa63e5a80e91b14684b2010e025617fe058c9cf2: android-backend-tests succeeded; android-cloud-build was skipped because the event was a pull request. This is backend-test evidence only. It is not a Gradle build, APK, emulator, UI, or benchmark acceptance result.
- The latest PR head at this audit update is aa63e5a80e91b14684b2010e025617fe058c9cf2. No manual cloud dispatch has been performed. No candidate-bound APK or emulator evidence exists.

Benchmark authority discrepancy (must be resolved before dispatch):
- experiments/android/esap-app-001/BENCHMARK_MANIFEST.json declares status FROZEN_V1 and records Git blob IDs for PROBLEM.md and ACCEPTANCE.json.
- The exact referenced PROBLEM.md still declares “Proposed benchmark specification; awaiting independent review and hash freeze.”
- The exact referenced ACCEPTANCE.json still declares PROPOSED_AWAITING_REVIEW_AND_HASH_FREEZE.
- The manifest's Git blob IDs match the current file versions inspected at this checkpoint, so this is not simply an old hash pointing at different bytes. It is an internal authority/status contradiction: the manifest says frozen while both normative source artifacts say proposed/unreviewed.
- The manifest provenance says the benchmark was newly defined after repository search and explicitly does not claim a previously approved organizational requirement. This is transparent provenance, but it is not evidence of independent review/approval.
- Resolution required: obtain independent review and record its authority/evidence; then reconcile the statuses and freeze policy consistently, or explicitly retain the benchmark as proposed. Do not silently change either status, and do not call the benchmark approved based solely on the manifest.
- Repository tree inspection at this head found only the three ESAP-APP-001 benchmark files plus the capability-gap audit under matching benchmark/authoritative-specification path terms. No separate esap-app-001-authoritative-specification.md artifact was found in that tree. This is a bounded path/name search, not proof that no differently named source exists elsewhere.

Current disposition:
- Android campaign backend contract tests: PASS on the latest commit's PR workflow.
- Android cloud build and emulator: NOT RUN.
- Approved source-to-ISR derivation: NOT ESTABLISHED; no approved derivation manifest or authoritative ISR revision is present.
- Benchmark authority: CONFLICTED / REVIEW REQUIRED.
- ESAP-APP-001 Stage A: BLOCKED. No AC criterion is upgraded by the backend-test run.


5.4 Latest CI and governance-review gate reconciliation (2026-11-03):
- Re-fetched PR #201 at head 6430e33a0dd600b0ccd9c472f9bc2ff5d70455cd and queried commit-associated pull-request workflow runs.
- GitHub Actions run 41636374374 (run #36) completed successfully on this head. Job android-backend-tests succeeded. Job android-cloud-build was skipped. This supersedes the earlier statement that no workflow run was found for the latest audit commit.
- The successful job is the campaign Android backend contract test suite only. It does not establish a Gradle build, APK, emulator install/launch, native UI behavior, source-to-ISR semantic derivation, or any AC-001 through AC-013 benchmark pass.
- Reviewed folder/prefull.md, “FS-00 — Full-Stack Compiler Architectural Reconnaissance & Foundation Gate”, especially §3.2 and §10.6. It requires the four FS-00 deliverables to be reviewed and states that a human reviewer (or lead architect) approves after the evidence classes are met. This is a repository governance precedent for explicit human approval; it does not by itself designate the authorized independent reviewer for ESAP-APP-001.
- PR #201 currently has no requested reviewers and no review/comment records returned by the PR discussion endpoint. Therefore no independent benchmark review or approval is evidenced in this PR.
- Required action before changing benchmark authority: identify the authorized independent reviewer (or lead architect if that role is permitted for this benchmark), provide the exact PROBLEM.md, ACCEPTANCE.json and manifest bytes/hashes for review, record findings and approval/rejection in a durable review artifact or signed/traceable PR review, and only then reconcile the three status fields under an explicit versioned freeze decision. A PR author’s commit or matching Git blob hashes are not independent approval.
- No benchmark files or status fields were changed in this checkpoint.

Updated disposition:
- Latest Android campaign backend contract tests on head 6430e33a: PASS (run #36).
- Android cloud build/APK/emulator: NOT RUN (job skipped).
- Independent benchmark review/approval: NOT EVIDENCED; authorized reviewer not identified.
- Benchmark authority: CONFLICTED / REVIEW REQUIRED.
- ESAP-APP-001 Stage A: BLOCKED. No AC criterion is upgraded by run #36.


5.5 Approval-authority and governance-mechanism inspection (2026-11-03):
- Inspected `folder/masterprompt.md`, `folder/prefull.md`, `folder/31.md`, `constitutional_architecture/governance/schemas.py`, `constitutional_architecture/governance/approval_workflow.py`, `certification/governance/escalation_policy.py`, and compiler ADR-012/ADR-013.
- `folder/prefull.md` states that FS-00 is non-mutating and its four deliverables must be committed and reviewed; the Compiler Architecture ADR must be approved before the later ISR↔Compiler IR contract and backend/artifact contracts proceed. It identifies review by a human reviewer or lead architect as a precedent, but does not name the person/team/role authorized to independently approve this Android benchmark. The repository path/name search did not identify the four FS-00 deliverables as a complete reviewed package. This is a bounded search; it does not establish that no differently named or external approval artifact exists.
- `docs/adr/ADR-012-compiler-backend-system.md` and `docs/adr/ADR-013-compiler-behavioral-certification.md` both have status "Proposed (pending certification)". They describe the existing compiler substrate and certification design, but neither designates an ESAP-APP-001 benchmark approver or proves the Android benchmark's authority.
- `constitutional_architecture/governance/schemas.py` supports approver categories HUMAN, ROLE, ORGANIZATION, AUTONOMOUS_AGENT and FEDERATION_COUNCIL. This is a generic schema vocabulary, not an assignment of an authorized independent reviewer to ESAP-APP-001.
- `ApprovalWorkflowEngine` in `constitutional_architecture/governance/approval_workflow.py` stores approvals in process-local dictionaries. Its `submit_decision(approval_id, decision, ...)` method does not itself accept or authenticate the identity of the submitting actor. Therefore the existence of this class alone cannot establish reviewer identity, independence, or durable approval evidence. A separate authenticated, durable record or GitHub review by an authorized independent reviewer is still required.
- `certification/governance/escalation_policy.py` defines escalation triggers and an explicit high-stakes operation allow-list. It documents human escalation as a boundary, but does not itself establish the benchmark's designated reviewer or a benchmark-specific approval workflow.
- No `.github/CODEOWNERS` or root `CODEOWNERS` file was found at this branch head. PR #201 has no requested reviewers and the review-submission query returned an empty list. This supports "no review recorded here", not "no qualified reviewer exists".
- Governance scope note: `folder/prefull.md` governs the Full-Stack Compiler's architecture-first construction sequence. PR #201 adds an Android backend plugin to an existing compiler substrate; the inspected material does not conclusively establish whether that work is subject to the FS-00 implementation gate. Do not classify this PR as a proven governance violation without an explicit scope ruling.
- Required resolution: obtain an explicit designation of the independent reviewer/lead architect and the approval authority applicable to ESAP-APP-001; record the reviewer identity, independence/conflict check, exact reviewed file hashes, findings, decision, timestamp and evidence reference in a durable review artifact. Then reconcile the manifest/problem/acceptance statuses under a versioned decision. Do not infer authority from a generic role enum, an unverified approval class, Git blob hashes, or PR authorship.

Updated disposition:
- Latest Android campaign backend contract tests: PASS on PR head 6430e33a (run #36).
- Android cloud build/APK/emulator: NOT RUN (PR event skipped the manual workflow).
- Independent benchmark review/approval: NOT EVIDENCED; reviewer authority remains unidentified.
- Existing governance framework: generic human/role approval concepts exist, but no benchmark-specific authorized reviewer mapping or authenticated durable approval record was established by this inspection.
- Benchmark authority: CONFLICTED / REVIEW REQUIRED.
- ESAP-APP-001 Stage A: BLOCKED. No AC criterion is upgraded.
