#!/usr/bin/env bash
#
# run-campaign-a.sh — Campaign A behavioral run (39 workloads × 2 backends = 78 trials).
# Produces evidence ledger + aggregate.  Independent verifier + campaign verdict.
#
# Exit codes: 0=CERTIFIED, 1=NOT_CERTIFIED, 3=QUALIFIED_PARTIAL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/release/evidence"

echo "=== Campaign A: 39 workloads × 2 backends ==="

cd "$REPO_ROOT"
python -m certification.campaign.campaign_a

echo "=== Verifying evidence ledger ==="
python -c "
from certification.evidence.ledger import EvidenceLedger
from certification.corpus.corpus import default_corpus
import sys
path = 'release/evidence/cbc1-a-ledger.jsonl'
ok = EvidenceLedger.verify(path)
count = EvidenceLedger.count(path)
expected = len(default_corpus()) * 2
print(f'Ledger: {count}/{expected} records, chain_valid={ok}')
sys.exit(0 if ok and count == expected else 1)
"

echo "=== Campaign verdict ==="
python -c "
import json, sys
with open('release/evidence/cbc1-a-aggregate.json') as f:
    agg = json.load(f)
verdict = agg.get('verdict', 'NOT_CERTIFIED')
reason = agg.get('verdict_reason', '')
total = agg.get('total_trials', 0)
certified = agg.get('certified', 0)
print(f'Verdict: {verdict}')
print(f'Reason:  {reason}')
print(f'Result:  {certified}/{total} trials certified')
print(f"Evidence ledger verification: {agg.get('evidence_ledger_verification_ok', agg.get('independent_verify_ok', False))}")
full_stack = agg.get('full_stack_verification', {})
if full_stack:
    print(f"Full-stack semantic verification: {full_stack.get('status', 'unknown')} "
          f"({full_stack.get('source_bound_trials_passed', 0)}/{full_stack.get('required_trials', total)} source-bound trials passed)")
    blockers = full_stack.get('blockers', [])
    if blockers:
        print('Top semantic/architecture blockers:')
        for blocker in blockers[:10]:
            print(f'  - {blocker}')
        if len(blockers) > 10:
            print(f'  ... {len(blockers) - 10} additional blocker(s) in cbc1-a-aggregate.json')
print()
print('Category matrix:')
for cat, backends in agg.get('category_matrix', {}).items():
    print(f'  {cat}: {backends}')
if agg.get('failure_taxonomy_independent'):
    print()
    print('Stage failure taxonomy (ledger replay):')
    for stage, count in agg['failure_taxonomy_independent'].items():
        print(f'  {stage}: {count}')
if agg.get('independent_verify_problems'):
    print()
    print('Independent verify problems:')
    for p in agg['independent_verify_problems']:
        print(f'  {p}')
print()
exit_codes = {'CERTIFIED': 0, 'NOT_CERTIFIED': 1, 'QUALIFIED_PARTIAL': 3}
sys.exit(exit_codes.get(verdict, 1))
"
