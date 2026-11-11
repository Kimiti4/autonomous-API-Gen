# ESAP-APP-001 Android cloud source binding

The manual Android cloud workflow no longer accepts a free-standing `SystemModel`.
It requires a serialized campaign `ISRRevision`, the exact benchmark source file,
and a source-to-ISR derivation manifest matching
`android_source_binding_manifest.schema.json`.

Before dispatch:

1. The benchmark specification must have an explicit approval/review decision.
   The current repository problem/acceptance artifacts must not be treated as
   approved merely because the manifest labels a freeze; their internal status
   fields currently still say `PROPOSED_AWAITING_REVIEW_AND_HASH_FREEZE`.
2. A qualified reviewer must establish that the ISR graph was derived from the
   exact source specification without dropping, inventing, or weakening
   requirements. The workflow does not create or infer this mapping.
3. Commit the specification, serialized `ISRRevision`, and binding manifest
   at the requested source revision.
4. Compute SHA-256 for the binding manifest and provide it as
   `expected_derivation_manifest_sha256` at manual dispatch. The workflow
   independently checks the source bytes, revision bytes, revision content
   hash, and manifest hash.
5. The workflow calls `compile_isr_revision`, which uses the campaign
   `isr_to_plan()` lowering and `AndroidStructuralBackend`, then
   `NativeAndroidStructuralRunner.execute_bound()` re-derives the plan and
   candidate before Gradle/APK/emulator execution.

The manifest is a pinned assertion, not a cryptographic reviewer signature.
Its approval must be established through repository review/governance before
dispatch. Do not use a test fixture, hand-written substitute graph, or
unapproved source as the benchmark input.

The Android backend currently supports only a static catalogue shell and
rejects runtime semantics. Therefore a faithful ESAP-APP-001 revision that
contains CRUD, validation, search, persistence, and offline behavior is
expected to be refused before APK generation until those semantics are
implemented. That refusal is the correct fail-closed result; it is not a cloud
build failure and must not be bypassed by stripping requirements.

A successful Gradle build, APK inspection, install, and launch is structural
execution evidence only. It does not satisfy runtime acceptance criteria
AC-002 through AC-012 or certify ESAP-APP-001. The benchmark verdict remains
BLOCKED until all criteria have direct, candidate-bound evidence and independent
semantic verification.
