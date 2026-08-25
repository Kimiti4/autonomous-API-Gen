#!/usr/bin/env bash
#
# run-v1.3-gates.sh — v1.3 Evolution Engine certification orchestrator (ADR-011).
#
# Same framework as run-v1.2-gates.sh: fail-closed, evidence-producing,
# bounded verdict CERTIFIED | NOT_CERTIFIED.
#
# AUTHORITATIVE RELEASE VERDICT REMAINS THE CI WORKFLOW.
# This runner produces evidence and a local/pre-flight verdict.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$REPO_ROOT/release/evidence/$RUN_ID"

mkdir -p "$EVIDENCE_DIR"
printf '%s' "$RUN_ID" > "$REPO_ROOT/release/evidence/.latest-run-id"

REQUIRED_GATES=(
  e0-inventory
  e1-genome-determinism
  e2-valid-genome
  e3-mutation-validity
  e4-crossover-validity
  e5-pareto-sort
  e6-lineage-materialization
  e7-invariants
  e8-stage-replaceability
  e9-selection-correctness
  e10-pipeline-composition
  e11-adapter-conformance
)

# ------------------------------------------------------- helpers
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# ------------------------------------------------------- aggregate writer
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
    echo "  version: v1.3"
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

# ------------------------------------------------------- stage runner (fail-closed)
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

# ---------------------------------------------------------------- RUNNING marker
cat >"$EVIDENCE_DIR/run.yaml" <<EOF
run_id: $RUN_ID
state: RUNNING
started_at: $(now_iso)
verdict_space: [CERTIFIED, NOT_CERTIFIED]
EOF
echo "POC v1.3 Evolution Engine certification run: $RUN_ID (evidence: $EVIDENCE_DIR)"

# ================================================================ GATES

# E0 — artifact inventory
run_stage e0-inventory \
  "cd '$REPO_ROOT' && python -c \"
import os, sys
manifest = [l.strip() for l in open('release/poc-v1.3-manifest.lst') if l.strip()]
missing = [f for f in manifest if not os.path.exists(f)]
if missing:
    print('E0 FAIL — missing:', missing, file=sys.stderr); sys.exit(1)
print('E0 PASS —', len(manifest), 'artifacts present')
\""

# E1 — genome determinism
run_stage e1-genome-determinism \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e1' -q"

# E2 — valid genome
run_stage e2-valid-genome \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e2' -q"

# E3 — mutation validity
run_stage e3-mutation-validity \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e3' -q"

# E4 — crossover validity
run_stage e4-crossover-validity \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e4' -q"

# E5 — Pareto sort correctness
run_stage e5-pareto-sort \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e5' -q"

# E6 — lineage + materialization
run_stage e6-lineage-materialization \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e6' -q"

# E7 — ADR-008 invariants on materialized graph
run_stage e7-invariants \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e7' -q"

# E8 — stage replaceability (static scan)
run_stage e8-stage-replaceability \
  "cd '$REPO_ROOT' && python release/gates/v1.3/check_stage_replaceability.py"

# E9 — selection correctness
run_stage e9-selection-correctness \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e9' -q"

# E10 — pipeline composition
run_stage e10-pipeline-composition \
  "cd '$REPO_ROOT' && python -m pytest tests/v13/test_evolution_gates.py -k 'test_e10' -q"

# E11 — adapter conformance (part of E8 static scan)
run_stage e11-adapter-conformance \
  "cd '$REPO_ROOT' && python release/gates/v1.3/check_stage_replaceability.py"

# ================================================================ FINAL AGGREGATE
write_aggregate
if grep -q '^  verdict: CERTIFIED$' "$EVIDENCE_DIR/aggregate.yaml"; then
  echo "RELEASE ELIGIBLE: CERTIFIED"
  exit 0
else
  echo "RELEASE BLOCKED: NOT_CERTIFIED" >&2
  exit 1
fi
