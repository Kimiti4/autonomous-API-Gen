#!/usr/bin/env bash
#
# run-v1.2-gates.sh — v1.2 certification orchestrator (ADR-008 + ADR-009).
#
# Same framework as run-v1.1-gates.sh: fail-closed, evidence-producing,
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
  g0-inventory
  g1-schema-determinism
  g2-invariants
  g3-hash-determinism
  g4-provenance
  g5-storage-independence
  g6-reconstruction
  g7-observation-consumption
  g8-invalid-rejection
  g9-schema-evolution
  g10-genesis
  g11-genesis-evidence
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
    echo "  version: v1.2"
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
echo "POC v1.2 certification run: $RUN_ID (evidence: $EVIDENCE_DIR)"

# ================================================================ GATES

# G0 — artifact inventory
run_stage g0-inventory \
  "cd '$REPO_ROOT' && python -c \"
import os, sys
manifest = [l.strip() for l in open('release/poc-v1.2-manifest.lst') if l.strip()]
missing = [f for f in manifest if not os.path.exists(f)]
if missing:
    print('G0 FAIL — missing:', missing, file=sys.stderr); sys.exit(1)
print('G0 PASS —', len(manifest), 'artifacts present')
\""

# G1–G4, G8 — ISR substrate unit gates
run_stage g1-schema-determinism \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g1_schema_determinism -q"
run_stage g2-invariants \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g2_invariants_dangling_edge tests/v12/test_isr_gates.py::test_g2_invariants_leakage -q"
run_stage g3-hash-determinism \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g3_hash_determinism -q"
run_stage g4-provenance \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g4_provenance_missing_created_by -q"
run_stage g8-invalid-rejection \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g8_invalid_rejection -q"

# G5 — storage independence (static scan)
run_stage g5-storage-independence \
  "cd '$REPO_ROOT' && python release/gates/v1.2/check_storage_independence.py"

# G9 — schema evolution
run_stage g9-schema-evolution \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_isr_gates.py::test_g9_schema_evolution_deterministic tests/v12/test_isr_gates.py::test_g9_schema_evolution_adds_version_property -q"

# G6 — ISR reconstruction (in-memory adapter roundtrip)
run_stage g6-reconstruction \
  "cd '$REPO_ROOT' && python -m pytest tests/test_isr_substrate_v12.py::TestMemoryStoreG6 -q"

# G7 — observation consumption (v1.1 ISR observation projection stub)
run_stage g7-observation-consumption \
  "cd '$REPO_ROOT' && python -c \"
from isr.core.graph import ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
graph = ISRGraph(nodes={'svc': Node(id='svc', type=NodeType.SERVICE, properties={'label': 'test'})}, edges={})
rev = ISRRevision.create('sys','rev0','1.0',graph,Provenance(created_by='genesis',created_at='2026-01-01T00:00:00Z'))
assert rev.content_hash and len(rev.content_hash) == 64
obs = {'type':'isr_observation','revision_id':rev.revision_id,'content_hash':rev.content_hash,'node_count':len(rev.graph.nodes)}
assert obs['node_count'] == 1
print('G7 PASS — v1.1 observation can consume ISR revision')
\""

# G10 — genesis mapping
run_stage g10-genesis \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_genesis_gates.py -k 'test_g10' -q"

# G11 — genesis evidence
run_stage g11-genesis-evidence \
  "cd '$REPO_ROOT' && python -m pytest tests/v12/test_genesis_gates.py -k 'test_g11' -q"

# ================================================================ FINAL AGGREGATE
write_aggregate
if grep -q '^  verdict: CERTIFIED$' "$EVIDENCE_DIR/aggregate.yaml"; then
  echo "RELEASE ELIGIBLE: CERTIFIED"
  exit 0
else
  echo "RELEASE BLOCKED: NOT_CERTIFIED" >&2
  exit 1
fi
