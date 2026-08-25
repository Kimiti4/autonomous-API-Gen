#!/usr/bin/env bash
#
# run-v1.1-gates.sh — POC v1.1 integration orchestrator (pre-flight evidence runner).
#
# Fail-closed and evidence-producing. Every stage yields a machine-readable
# evidence record; the aggregate verdict is computed from those records
# (exit status + declared artifacts), NEVER from console text.
#
# Verdict space is bounded: CERTIFIED | NOT_CERTIFIED. No QUALIFIED_PARTIAL —
# "pending build" is an execution state, not a verdict.
#
# AUTHORITATIVE RELEASE VERDICT REMAINS THE CI WORKFLOW
# (.github/workflows/v1.1-release-gate.yml). This runner produces evidence and
# a local/pre-flight verdict; it is not the release gate itself.
#
# No `|| true`, no swallowed subprocess status, no warning standing in for a
# failed mandatory assertion.

set -euo pipefail

# ---------------------------------------------------------------- locations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$REPO_ROOT/release/evidence/$RUN_ID"
COMPOSE_FILE="$REPO_ROOT/autonomous-api/tests/integration/docker-compose.yml"

mkdir -p "$EVIDENCE_DIR"

# Expose the run id for CI evidence archival. Written first so it exists even
# if the run fails early — failure evidence must be archivable too.
printf '%s' "$RUN_ID" > "$REPO_ROOT/release/evidence/.latest-run-id"

# ------------------------------------------------------- required gates (ordered)
REQUIRED_GATES=(
  gate-1a-schema
  gate-1b-parity
  gate-4-source
  gate-6-freshness
  gate-6-client-build
  gate-6-dashboard-build
  gate-4-dist-only
  v1-07-pg-sequence
  reducer-equivalence
  snapshot-integrity
  dashboard-validation
)

# ------------------------------------------------------- Postgres lifecycle
PG_UP=0
pg_up()   { if [ "$PG_UP" -eq 0 ]; then docker compose -f "$COMPOSE_FILE" up -d --wait; PG_UP=1; fi; }
pg_down() { if [ "$PG_UP" -eq 1 ]; then docker compose -f "$COMPOSE_FILE" down -v || true; PG_UP=0; fi; }
trap pg_down EXIT

# ------------------------------------------------------- helpers
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# ------------------------------------------------------- aggregate writer
# Release certification manifest: binds each gate's evidence.yaml by SHA-256
# (transitively binding the stdout/stderr hashes inside it), separates
# missing_evidence from failed_gates, and carries release.version. The CI
# release job verifies THIS artifact — never console text or exit codes.
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
    echo "  version: v1.1"
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

  # bash -c always runs; a non-zero exit is captured, never swallowed.
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
    write_aggregate                     # this gate not PASS -> NOT_CERTIFIED
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
echo "POC v1.1 integration run: $RUN_ID (evidence: $EVIDENCE_DIR)"

# ================================================================ STAGES
# Gate 1 — contract integrity (schema golden stability + cross-language parity)
run_stage gate-1a-schema \
  "cd '$REPO_ROOT' && python release/gates/gate1/extract_contract_schema.py --check release/gates/gate1/contract-schema.json"
run_stage gate-1b-parity \
  "cd '$REPO_ROOT' && python release/gates/gate1/verify_contract_parity.py"

# Gate 4 — source/CSP scan (pre-build context; dist absence is informational here)
run_stage gate-4-source \
  "cd '$REPO_ROOT' && python release/gates/gate4/security_scan.py"

# Gate 6 — generated-artifact freshness + builds (owns build responsibility)
run_stage gate-6-freshness \
  "cd '$REPO_ROOT' && python release/gates/gate6/verify_artifacts.py"
run_stage gate-6-client-build \
  "cd '$REPO_ROOT/observation-client' && npm ci && npm run build"
run_stage gate-6-dashboard-build \
  "cd '$REPO_ROOT/dashboard' && npm ci && npm run build"

# Gate 4 — post-build shipped-artifact scan (downstream of Gate 6 builds;
# dist MUST exist or this FAILS — no vacuous pass)
run_stage gate-4-dist-only \
  "cd '$REPO_ROOT' && python release/gates/gate4/security_scan.py --dist-only"

# Integration — PostgreSQL-backed durability evidence (V1-07).
# pg_sequence_store fixture lives in autonomous-api/tests/conftest.py;
# compose service pg-test exposes :5433 matching the fixture default DSN.
pg_up
run_stage v1-07-pg-sequence \
  "cd '$REPO_ROOT/autonomous-api' && python -m pytest tests/observation/test_sequence_concurrency_pg.py tests/observation/test_sequence_concurrency.py -m integration -q"
run_stage reducer-equivalence \
  "cd '$REPO_ROOT/autonomous-api' && python -m pytest tests/observation/test_reducer_equivalence.py tests/observation/test_provenance_integrity.py -q"
run_stage snapshot-integrity \
  "cd '$REPO_ROOT/autonomous-api' && python -m pytest tests/observation/test_snapshot_data_aggregator.py -q"
pg_down

# Integration — dashboard behavioral validation (fresh client -> dashboard)
run_stage dashboard-validation \
  "cd '$REPO_ROOT/dashboard' && npm run typecheck && npm run test"

# ================================================================ FINAL AGGREGATE
write_aggregate
if grep -q '^  verdict: CERTIFIED$' "$EVIDENCE_DIR/aggregate.yaml"; then
  echo "RELEASE ELIGIBLE: CERTIFIED"
  exit 0
else
  echo "RELEASE BLOCKED: NOT_CERTIFIED" >&2
  exit 1
fi
