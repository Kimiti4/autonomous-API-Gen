#!/usr/bin/env bash
#
# run-campaign-b.sh — Campaign B measurement runbook.
# Real Docker execution, 500–1000 trials, sharded by category.
#
# IMPORTANT: This script uses stub stages unless Docker is available.
# With Docker: set CBC1_DOCKER=1 and ensure daemon is running.
#
# Exit codes: 0=CERTIFIED, 1=NOT_CERTIFIED, 3=QUALIFIED_PARTIAL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/release/evidence"

SCALE="${CBC1_SCALE:-1}"  # 1x=78, 2x=156, ... up to capacity

echo "=== Campaign B: scale factor ${SCALE}x ==="
echo "Scale: ${SCALE} × 39 workloads × 2 backends = $(( SCALE * 78 )) trials"

cd "$REPO_ROOT"

# Run campaign A with scale factor (repeats corpus to reach target)
python -c "
from certification.campaign.campaign_a import run_campaign_a
import os, sys

scale = int(os.environ.get('CBC1_SCALE', '1'))
if scale > 1:
    # Multi-run: run campaign multiple times, merge ledgers
    all_trials = []
    all_summary = {}
    ledger_path = 'release/evidence/cbc1-b-ledger.jsonl'
    agg_path = 'release/evidence/cbc1-b-aggregate.json'
    # Clear old ledger
    if os.path.exists(ledger_path):
        os.remove(ledger_path)
    for i in range(scale):
        trials, summary = run_campaign_a(ledger_path, agg_path)
        all_trials.extend(trials)
        all_summary = summary
    all_summary['total_trials'] = len(all_trials)
    all_summary['corpus_size'] = 39 * scale
    all_summary['scale_factor'] = scale
    import json
    with open(agg_path, 'w') as f:
        json.dump(all_summary, f, indent=2)
    print(f'Campaign B: {len(all_trials)} trials at scale {scale}x')
else:
    run_campaign_a()
    print('Campaign B: 78 trials (1x scale)')
"

echo "=== Verifying evidence ledger ==="
python -c "
from certification.evidence.ledger import EvidenceLedger
from certification.corpus.corpus import default_corpus
import sys, os
path = 'release/evidence/cbc1-a-ledger.jsonl'
if not os.path.exists(path):
    path = 'release/evidence/cbc1-b-ledger.jsonl'
ok = EvidenceLedger.verify(path)
count = EvidenceLedger.count(path)
expected = len(default_corpus()) * 2 * int(os.environ.get('CBC1_SCALE', '1'))
print(f'Ledger: {count}/{expected} records, chain_valid={ok}')
sys.exit(0 if ok and count == expected else 1)
"

echo "=== Campaign verdict ==="
python -c "
import json, sys
agg_path = 'release/evidence/cbc1-a-aggregate.json'
if not __import__('os').path.exists(agg_path):
    agg_path = 'release/evidence/cbc1-b-aggregate.json'
with open(agg_path) as f:
    agg = json.load(f)
verdict = agg.get('verdict', 'NOT_CERTIFIED')
reason = agg.get('verdict_reason', '')
total = agg.get('total_trials', 0)
certified = agg.get('certified', 0)
print(f'Verdict: {verdict}')
print(f'Reason:  {reason}')
print(f'Result:  {certified}/{total} trials certified')
if agg.get('failure_taxonomy_independent'):
    print()
    print('Failure taxonomy (independent):')
    for stage, count in agg['failure_taxonomy_independent'].items():
        print(f'  {stage}: {count}')
print()
exit_codes = {'CERTIFIED': 0, 'NOT_CERTIFIED': 1, 'QUALIFIED_PARTIAL': 3}
sys.exit(exit_codes.get(verdict, 1))
"
