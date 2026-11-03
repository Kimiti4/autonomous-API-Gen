ESAP-APP-001 — Authoritative Benchmark Specification
Status: SPECIFICATION ONLY — benchmark BLOCKED (Stage A prerequisites absent)
Branch: remediation/esap-android-compiler-stage-a
Verified commits: 6d62866 (binding gate), 2624083 (canonical binding tests), 719580d4 (workflow with fail-closed compiler check), 4e244897 (audit evidence), c6ac140e (compiler interfaces)

This file defines the authoritative requirements and compilation path. It does not claim any executed runtime evidence, any APK build, or any emulator verification — those remain BLOCKED.

1. Canonical source-binding chain (truthful, fail-closed):
- Benchmark artifact: this file (ESAP-APP-001 requirements specification)
- Requirements graph: derived from this file; graph identity recorded as hash
- ISR revision: derived from requirements graph; revision identity = content hash
- Compilation plan: derived from ISR revision; plan identity = content hash
- Generated candidate: must bind to exact source revision (`git rev-parse HEAD` at build time); candidate hash = SHA-256 of emitted bundle
- Evidence: `candidate-binding.json` must contain `requirements_model_path`, `system_model_content_hash`, `source_revision`, `candidate_id`, `apk_sha256` (only when APK exists)

2. Grocery-list requirements (minimum, truthful, not invented beyond specification):
- Required operations (inventory application):
  - Create item (name, quantity, category, notes)
  - Read/view item list (search/filter by name/category)
  - Update item (quantity, notes)
  - Delete item (with authorization check)
- Authorization rules (per authorization contract):
  - `inventory.create`: requires `inventory.read` permission
  - `inventory.read`: public (no deny rules)
  - `inventory.update`: requires `inventory.write` permission
  - `inventory.delete`: requires `inventory.admin` permission; fails closed if authorization binding missing
- Persistence expectation (durable state — NOT YET VERIFIED at runtime):
  - Application state must survive restart; evidence from durable ledger adapter (`compiler/core/ledger.py`) defines contract but durable cross-process execution is still open per W02 contract
- Offline expectation (NOT YET VERIFIED): application must function without network; verification requires emulator/test with network disabled

3. Acceptance criteria (gates; all must pass with real evidence before upgrade):
- Requirement-to-source traceability: `ESAP-APP-001` specification → `requirements_model_path` → `ISRRevision` → `CompilationPlan`
- Source-to-candidate binding: generated APK hash matches `candidate-binding.json`; source SHA matches `inputs.source_revision`
- Authorization enforcement: every route/action has authorization binding; fails closed if missing (verified by authorization contract)
- Effect contract: executable effects must have complete contracts (`precondition`, `authorized_operation`, `permitted_side_effect`, `failure_behavior`, `postcondition`); partial contracts fail at model creation (verified by effect contract tests: 12 pass)
- Durable ledger: rejected attempts (authorization failure, missing contract) produce NO ledger entry; committed executions produce chain-linked records (verified by `tests/cbc1/test_w02_w06_executable_effect_contract.py` — 12 pass; `compiler/core/ledger.py` — adapter-independent interface)
- Runtime verification (Stage B — NOT STARTED): APK installed; grocery-list CRUD executed; authorization enforced at runtime (fail-closed)
- Change-request regression (Stage D — NOT STARTED): requirement change → recompile → same authorization/effect/ledger checks pass; evidence references new candidate

4. Fail-closed rules (must never be overridden):
- If `android` compiler not registered → BLOCKED (not simulated PASS)
- If authorization binding missing → BLOCKED/FAILED (not simulated PASS)
- If effect contract incomplete → BLOCKED (model creation fails; not simulated PASS)
- If APK missing → BLOCKED (not simulated PASS)
- If APK hash doesn't match evidence → REJECTED
- If SDK/Gradle/emulator missing → BLOCKED (not simulated PASS)
- No fabricated clients, routes, forms, API clients; no payroll content; truthful capabilities (production_ready=False for ClickHouse telemetry; Android backend truthfully not production-certified)

5. Status preservation (hard constraints):
- W02/W06: IN_PROGRESS (not verified by module tests; full Rust EFFECT_EXECUTION and durable cross-process still open)
- W12: IN_PROGRESS (preservation complete; executable verification separate)
- W13: IN_PROGRESS (merged PRs #171-#176; not certified by count)
- W03: UPGRADED (durable adapter verified)
- W14: UPGRADED (LiveView/Scenic/Hologram fixtures + authorization verified)

6. Evidence provenance:
- Working tree files: `release/evidence/ESAP-APP-001_capability_gap_audit.md`, `ESAP-STAGE-A-build-capability.md`, `milestone_status_post_hardening.md`
- Compiler contracts: `compiler/core/authorization.py`, `compiler/core/ledger.py`, `compiler/core/effect_verification.py`
- Tests: `tests/cbc1/test_clickhouse_hardening.py` (3 pass), `test_fastapi_hardening.py` (3 pass), `test_w14_authorization_hardening.py` (2 pass), `test_w02_w06_executable_effect_contract.py` (12 pass)
- Workflow: `.github/workflows/android-cloud-build-certification.yml` (committed at 3f76a743 / 719580d4 / 4e244897; fails closed on missing compiler; uses actual interfaces; no simulated results)
- PR #201 (remediation/esap-android-compiler-stage-a): open; commits 3bda5e63 / 2624083 / 4bd9347b / 6d62866; CI not yet verified; no merge to `main`

Status: SPECIFICATION ONLY — BLOCKED for Stage A build; NOT STARTED for B/C/D.