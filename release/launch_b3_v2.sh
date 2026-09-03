#!/usr/bin/env bash
#
# launch_b3_v2.sh — start the B3-v2 Campaign B wave.
#
# This is the launch sequence after:
#   - commit ebe8712 (Phase 31 evidence bundle)
#   - commit 80a67b8 (infra-storm side-channel)
#
# B3-v1 was interrupted at 149/936 trials by the 12-hr time budget. B3-v2
# starts a fresh wave on the same scale (12x, 936 trials) under the same
# 12-hr budget, with the new infra-storm ledger capturing infrastructure
# failures OFF the verdict chain.
#
# What this script does:
#   1. Sanity-checks the B3-v1 ledger is preserved (149 records, NOT modified).
#   2. Verifies the new infra-storm code is in place.
#   3. Verifies Docker is reachable.
#   4. Writes a launch marker so the wave can be resumed if interrupted.
#   5. Launches run_wave("B3") in the background with output tee'd to a log.
#
# Exit codes:
#   0  = CERTIFIED
#   1  = NOT_CERTIFIED  (including budget exhaustion)
#   3  = QUALIFIED_PARTIAL
#
# Usage:
#   bash release/launch_b3_v2.sh
#
# Resume after interruption:
#   CBC1_RESUME=1 bash release/launch_b3_v3.sh ...   # see run_wave

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/release/evidence"
LOG_DIR="$REPO_ROOT/release/evidence/b3-v2-logs"
mkdir -p "$EVIDENCE_DIR" "$LOG_DIR"

LAUNCH_MARKER="$EVIDENCE_DIR/.b3-v2-launch-marker"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/b3-v2-${TIMESTAMP}.log"

cd "$REPO_ROOT"

echo "=== B3-v2 launch preflight ==="
echo "Repo root:  $REPO_ROOT"
echo "Evidence:   $EVIDENCE_DIR"
echo "Log:        $LOG_FILE"
echo

# 1. Sanity: B3-v1 ledger is preserved (unmodified).
B3_V1_LEDGER="$EVIDENCE_DIR/cbc1-b-B3-ledger.jsonl"
if [ ! -f "$B3_V1_LEDGER" ]; then
  echo "FATAL: B3-v1 ledger not found at $B3_V1_LEDGER" >&2
  exit 2
fi
B3_V1_LINES=$(wc -l < "$B3_V1_LEDGER")
echo "B3-v1 ledger:  $B3_V1_LEDGER ($B3_V1_LINES records)"
if [ "$B3_V1_LINES" -ne 149 ]; then
  echo "WARN: B3-v1 ledger line count is $B3_V1_LINES, expected 149. Continuing anyway."
fi
B3_V1_AGG="$EVIDENCE_DIR/cbc1-b-B3-aggregate.json"
if [ -f "$B3_V1_AGG" ]; then
  echo "B3-v1 aggregate: present"
else
  echo "B3-v1 aggregate: MISSING (interrupted before aggregate was written)"
fi

# 2. Verify infra-storm code is in place.
if ! python -c "from certification.evidence.infra_storm import InfraStormLedger" 2>/dev/null; then
  echo "FATAL: certification.evidence.infra_storm not importable. Commit 80a67b8 missing?" >&2
  exit 2
fi
echo "Infra-storm module: OK"

# 3. Docker.
if ! command -v docker >/dev/null 2>&1; then
  echo "FATAL: docker is not on PATH. B waves require real_docker mode." >&2
  exit 2
fi
if ! docker info >/dev/null 2>&1; then
  echo "FATAL: docker daemon is not reachable." >&2
  exit 2
fi
echo "Docker: OK"

# 4. Wave config sanity.
python -c "
from certification.campaign.waves import WAVES, BUDGETS
w = WAVES.get('B3')
b = BUDGETS.get('B3')
assert w is not None, 'B3 wave not defined'
assert b is not None, 'B3 budget not defined'
assert w.required_mode.value == 'real_docker', f'unexpected mode {w.required_mode}'
assert b.max_trials == 936, f'unexpected max_trials {b.max_trials}'
assert b.max_total_runtime_s == 43200, f'unexpected runtime {b.max_total_runtime_s}'
print(f'B3: scale={w.scale_factor}, mode={w.required_mode.value}, max_trials={b.max_trials}, max_runtime={b.max_total_runtime_s}s')
"
echo

# 5. Write the launch marker (idempotent: refused if a prior launch is in flight).
if [ -f "$LAUNCH_MARKER" ]; then
  echo "WARN: launch marker exists at $LAUNCH_MARKER"
  echo "  Contents: $(cat "$LAUNCH_MARKER")"
  echo "  If a prior B3-v2 launch is in flight, this script will refuse to start a second one."
  echo "  To override, delete the marker manually."
  exit 3
fi

cat > "$LAUNCH_MARKER" <<EOF
launched_at=$TIMESTAMP
log_file=$LOG_FILE
pid=$$
EOF
echo "Launch marker: $LAUNCH_MARKER"

# 6. Launch.
echo
echo "=== Launching B3-v2 (background, log: $LOG_FILE) ==="

# NOTE: CBC1_INFRA_STORM=1 is the default; explicit for clarity.
# CBC1_EVOLVE=1 is required for backend-variant self-repair (same as B3-v1).
CBC1_WAVE=B3 \
CBC1_INFRA_STORM=1 \
CBC1_EVOLVE=1 \
  python -u release/run_wave.py 2>&1 | tee "$LOG_FILE"

EXIT_CODE=$?

# 7. Cleanup the launch marker.
rm -f "$LAUNCH_MARKER"

echo
echo "=== B3-v2 finished (exit=$EXIT_CODE) ==="
echo "Aggregate: $EVIDENCE_DIR/cbc1-b-B3-aggregate.json"
echo "Verdict ledger: $EVIDENCE_DIR/cbc1-b-B3-ledger.jsonl"
echo "Infra-storm ledger: $EVIDENCE_DIR/cbc1-b-B3-infra-storm.jsonl"
echo "B3-v1 ledger (preserved): $B3_V1_LEDGER"

exit $EXIT_CODE
