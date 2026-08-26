#!/usr/bin/env bash
#
# run-cbc1.sh — ADR-013 CBC-1 behavioral certification orchestrator (B0-B9).
# Same framework: fail-closed, evidence-producing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$REPO_ROOT/release/evidence/$RUN_ID"

mkdir -p "$EVIDENCE_DIR"
printf '%s' "$RUN_ID" > "$REPO_ROOT/release/evidence/.latest-run-id"

REQUIRED_GATES=(
  b0-inventory
  b1-trial-model
  b2-stage-protocols
  b7-verdict-composition
  b8-metrics-four-class
  b9-campaign-aggregation
  b-corpus-coverage
  b-full-stub-trial
  b-independent-verify
  b-cbc1-independence
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
    echo "  version: cbc1"
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
echo "ADR-013 CBC-1 certification run: $RUN_ID (evidence: $EVIDENCE_DIR)"

# ================================================================ GATES

run_stage b0-inventory \
  "cd '$REPO_ROOT' && python -c \"
import os, sys
manifest = [l.strip() for l in open('release/poc-cbc1-manifest.lst') if l.strip()]
missing = [f for f in manifest if not os.path.exists(f)]
if missing:
    print('B0 FAIL — missing:', missing, file=sys.stderr); sys.exit(1)
print('B0 PASS —', len(manifest), 'artifacts present')
\""

run_stage b1-trial-model \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py -k 'test_b1' -q"

run_stage b2-stage-protocols \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py::test_b2_stage_protocols_enforceable -q"

run_stage b7-verdict-composition \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py::test_b7_full_verdict_all_conditions -q"

run_stage b8-metrics-four-class \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py -k 'test_b8' -q"

run_stage b9-campaign-aggregation \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py::test_b9_campaign_aggregation -q"

run_stage b-corpus-coverage \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py -k 'test_default_corpus' -q"

run_stage b-full-stub-trial \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py::test_full_stub_trial_certified -q"

run_stage b-independent-verify \
  "cd '$REPO_ROOT' && python -m pytest tests/cbc1/test_cbc1_gates.py::test_independent_verify_separate_process -q"

run_stage b-cbc1-independence \
  "cd '$REPO_ROOT' && python release/gates/cbc1/check_certification_independence.py"

# ================================================================ FINAL AGGREGATE
write_aggregate
if grep -q '^  verdict: CERTIFIED$' "$EVIDENCE_DIR/aggregate.yaml"; then
  echo "RELEASE ELIGIBLE: CERTIFIED"
  exit 0
else
  echo "RELEASE BLOCKED: NOT_CERTIFIED" >&2
  exit 1
fi
