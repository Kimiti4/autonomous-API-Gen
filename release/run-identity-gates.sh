#!/usr/bin/env bash
#
# run-identity-gates.sh — ADR-010 Identity certification orchestrator (I0-I9).
# Same framework as run-v1.2-gates.sh: fail-closed, evidence-producing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$REPO_ROOT/release/evidence/$RUN_ID"

mkdir -p "$EVIDENCE_DIR"
printf '%s' "$RUN_ID" > "$REPO_ROOT/release/evidence/.latest-run-id"

REQUIRED_GATES=(
  i0-inventory
  i1-email
  i2-independence-leak
  i3-mfa
  i4-least-privilege
  i5-action-evidence
  i6-session
  i7-independence
  i8-password
  i9-recovery
)

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

write_aggregate() {
  local verdict="CERTIFIED"
  local missing_evidence=()
  local failed_gates=()
  local gate_lines=()
  local g ev st ec sha

  for g in "${REQUIRED_GATES[@]}"; do
    ev="$EVIDENCE_DIR/$g/evidence.yaml"
    if [ ! -f "$ev" ]; then
      verdict="NOT_CERTIFIED"; missing_evidence+=("$g")
      gate_lines+=("  $g:" "    status: MISSING" "    exit_code: null" "    evidence_sha256: null")
      continue
    fi
    st="$(sed -n 's/^status: //p' "$ev")"
    ec="$(sed -n 's/^exit_code: //p' "$ev")"
    sha="$(sha256_of "$ev")"
    if [ "$st" != "PASS" ]; then
      verdict="NOT_CERTIFIED"; failed_gates+=("$g")
    fi
    gate_lines+=("  $g:" "    status: ${st:-UNKNOWN}" "    exit_code: ${ec:-null}" "    evidence_sha256: $sha")
  done

  {
    echo "release:"
    echo "  version: identity-v1"
    echo "  run_id: $RUN_ID"
    echo "  verdict: $verdict"
    echo "  generated_at: $(now_iso)"
    echo "gates:"
    printf '%s\n' "${gate_lines[@]}"
    echo "certification:"
    echo "  required_gates:"
    for g in "${REQUIRED_GATES[@]}"; do echo "    - $g"; done
    if [ "${#missing_evidence[@]}" -eq 0 ]; then echo "  missing_evidence: []";
    else echo "  missing_evidence:"; for g in "${missing_evidence[@]}"; do echo "    - $g"; done; fi
    if [ "${#failed_gates[@]}" -eq 0 ]; then echo "  failed_gates: []";
    else echo "  failed_gates:"; for g in "${failed_gates[@]}"; do echo "    - $g"; done; fi
  } > "$EVIDENCE_DIR/aggregate.yaml"

  echo "AGGREGATE: $verdict -> $EVIDENCE_DIR/aggregate.yaml"
}

run_stage() {
  local gate="$1" command="$2"
  local gate_dir="$EVIDENCE_DIR/$gate"
  mkdir -p "$gate_dir"
  local started completed exit_code status
  started="$(now_iso)"
  set +e
  bash -c "$command" >"$gate_dir/stdout.log" 2>"$gate_dir/stderr.log"
  exit_code=$?
  set -e
  completed="$(now_iso)"
  status="PASS"; [ "$exit_code" -ne 0 ] && status="FAIL"
  cat >"$gate_dir/evidence.yaml" <<EOF
gate: $gate
status: $status
exit_code: $exit_code
command: $command
started_at: $started
completed_at: $completed
artifacts:
  - release/evidence/$RUN_ID/$gate/stdout.log
  - release/evidence/$RUN_ID/$gate/stderr.log
evidence:
  stdout_sha256: $(sha256_of "$gate_dir/stdout.log")
  stderr_sha256: $(sha256_of "$gate_dir/stderr.log")
EOF
  echo "[$status] $gate exit=$exit_code -> $gate_dir/evidence.yaml"
  if [ "$exit_code" -ne 0 ]; then
    write_aggregate
    echo "FAIL-CLOSED: gate '$gate' failed -> aggregate NOT_CERTIFIED" >&2
    exit 1
  fi
}

cat >"$EVIDENCE_DIR/run.yaml" <<EOF
run_id: $RUN_ID
state: RUNNING
started_at: $(now_iso)
verdict_space: [CERTIFIED, NOT_CERTIFIED]
EOF
echo "ADR-010 Identity certification run: $RUN_ID (evidence: $EVIDENCE_DIR)"

# ================================================================ GATES

run_stage i0-inventory \
  "cd '$REPO_ROOT' && python -c \"
import os, sys
manifest = [l.strip() for l in open('release/poc-identity-manifest.lst') if l.strip()]
missing = [f for f in manifest if not os.path.exists(f)]
if missing:
    print('I0 FAIL — missing:', missing, file=sys.stderr); sys.exit(1)
print('I0 PASS —', len(manifest), 'artifacts present')
\""

run_stage i1-email \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py -k 'test_i1' -q"

run_stage i2-independence-leak \
  "cd '$REPO_ROOT' && python release/gates/identity/check_identity_independence.py"

run_stage i3-mfa \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py::test_i3_mfa_stepup_cycle -q"

run_stage i4-least-privilege \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py -k 'test_i4' -q"

run_stage i5-action-evidence \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py::test_i5_action_to_v11_evidence -q"

run_stage i6-session \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py::test_i6_session_rotation_revocation -q"

run_stage i7-independence \
  "cd '$REPO_ROOT' && python release/gates/identity/check_identity_independence.py"

run_stage i8-password \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py::test_i8_password_hashing_secure -q"

run_stage i9-recovery \
  "cd '$REPO_ROOT' && python -m pytest tests/identity/test_identity_gates.py::test_i9_recovery_codes_single_use -q"

# ================================================================ FINAL AGGREGATE
write_aggregate
if grep -q '^  verdict: CERTIFIED$' "$EVIDENCE_DIR/aggregate.yaml"; then
  echo "RELEASE ELIGIBLE: CERTIFIED"
  exit 0
else
  echo "RELEASE BLOCKED: NOT_CERTIFIED" >&2
  exit 1
fi
