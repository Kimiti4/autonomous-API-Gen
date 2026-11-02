ESAP-APP-001 Stage A — Android Build Capability (Evidence-Gated)
Date: Mon Nov 02 2026
Status: BLOCKED (explicit — not simulated, not upgraded)
Block reason: Android SDK (ANDROID_HOME / ANDROID_SDK_ROOT) not set; SDK paths (opt/android-sdk, usr/lib/android-sdk, Library Android, snap/bin/android-sdk, LOCALAPPDATA Android) all absent; Gradle not in PATH; no gradlew or wrapper jar; emulator not available.

Evidence (working tree — independent confirmation blocked by 404 default branch):
- SDK_FOUND: NONE
- ENV: ANDROID_HOME=NOT SET, ANDROID_SDK_ROOT=NOT SET, ANDROID_STUDIO_INSTALL=NOT SET
- GRADLE_PROJECT: False
- Existing compiler: python-fastapi (runnable), clickhouse_telemetry (production_ready=False), 9 frontend fixtures
- Ledger interface: compiler/core/ledger.py (chain-linked evidence, rejected attempts produce no entry)
- Authorization: compiler/core/authorization.py (assert_authorization_enforceable; fail-closed)
- Effect contracts: compiler/core/effect_verification.py (12 pass, all-or-nothing validator)

What was attempted (not fabricated):
- Inspected actual SDK paths; none present.
- Checked ANDROID_HOME / ANDROID_SDK_ROOT env; not set.
- Checked Gradle binary / wrapper; not present.
- No APK generated (would require SDK + Gradle + dependency resolution + reproducible build inputs).

What CAN be documented truthfully (existing contracts applied):
- Build profile contract can be defined (language=java/kotlin, framework=gradle/android, required_files=build.gradle, AndroidManifest.xml, src/main/...) — but emission requires SDK.
- Authorization enforcement applies to any emitted route (fail-closed if authorization not enforceable).
- Durable ledger records only committed executions; rejected attempts (e.g., failed build, authorization refusal) leave no entry — negative control preserved.
- No new frontend target advertised (all 9 complete).
- No payroll content; no fabricated clients/forms/API clients.

Acceptance gate for Stage A (must all pass before upgrade):
1. SDK present (ANDROID_SDK_ROOT or ANDROID_HOME) — BLOCKED
2. Gradle wrapper/project present — BLOCKED
3. Dependency resolution succeeds — BLOCKED
4. APK output exists and has non-zero size — BLOCKED
5. Authorization contracts bind to emitted Android build paths — NOT YET APPLIED (blocked at 1)

Stage A status: BLOCKED. No upgrade of W02/W06/W12/W13. W03/W14 remain upgraded (verified on previous gates, unrelated to Android build). ESAP-APP-001 remains audit + blocked Stage A.
