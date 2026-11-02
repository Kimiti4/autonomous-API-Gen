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
- Android SDK / Gradle build pipeline not present.
- Emulator automation (Android Emulator / device farm) not present.
- APK packaging / signing not present.
- Device-level authentication (Android KeyChain / Biometric / OAuth2 mobile) not implemented.
- Persistent mobile storage (SQLite / Room / DataStore / encrypted file) not bound to effect contracts.
- Cross-device synchronization (realtime sync, conflict resolution) not represented in ISR behavior.
- Mobile UI test automation (Espresso / UI Automator / Appium) not present; Playwright artifacts cover web, not Android native.

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

File references (working branch — independent confirmation blocked by 404 on default branch):
- `release/evidence/milestone_status_post_hardening.md`
- `compiler/core/ledger.py`
- `tests/cbc1/test_clickhouse_hardening.py`
- `tests/cbc1/test_fastapi_hardening.py`
- `tests/cbc1/test_w14_authorization_hardening.py`
- `compiler/core/effect_verification.py`
- `compiler/core/authorization.py`
