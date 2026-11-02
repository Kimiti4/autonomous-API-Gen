import os
files = {
    'ESAP_AUDIT': 'release/evidence/ESAP-APP-001_capability_gap_audit.md',
    'STAGE_A_BLOCKED': 'release/evidence/ESAP-STAGE-A-build-capability.md',
    'HARDENING_STATUS': 'release/evidence/milestone_status_post_hardening.md',
    'LEDGER': 'compiler/core/ledger.py',
    'EFFECT_VERIFICATION': 'compiler/core/effect_verification.py',
    'AUTHORIZATION': 'compiler/core/authorization.py',
    'CLICKHOUSE': 'tests/cbc1/test_clickhouse_hardening.py',
    'FASTAPI_HARDEN': 'tests/cbc1/test_fastapi_hardening.py',
    'W14_HARDEN': 'tests/cbc1/test_w14_authorization_hardening.py',
    'W02_W06_CONTRACT': 'tests/cbc1/test_w02_w06_executable_effect_contract.py',
}
for label, p in files.items():
    print(f"{label}: {'PRESENT' if os.path.isfile(p) else 'MISSING'} ({p})")
print()
print("Status preservation (truthful):")
print("W02 W06: IN_PROGRESS (not upgraded)")
print("W12: IN_PROGRESS (preservation complete, not verified executable)")
print("W13: IN_PROGRESS (merged PRs, not certified by count)")
print("W03: UPGRADED (durable adapter verified)")
print("W14: UPGRADED (fixtures + authorization verified)")
print("ESAP-APP-001 Stage A: BLOCKED (SDK NONE, Gradle False, no APK produced)")
