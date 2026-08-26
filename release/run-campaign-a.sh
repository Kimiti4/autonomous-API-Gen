#!/usr/bin/env bash
#
# run-campaign-a.sh — Campaign A behavioral run (39 workloads × 2 backends = 78 trials).
# Produces evidence ledger + aggregate.  Independent verifier rejects dishonest results.

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

echo "=== Independent campaign verification ==="
python -c "
from certification.campaign.verify_campaign import verify_campaign
import json, sys
ok, matrix, taxonomy, problems = verify_campaign('release/evidence/cbc1-a-ledger.jsonl')
print(json.dumps({'matrix': matrix, 'failure_taxonomy': taxonomy}, indent=2))
if problems:
    for p in problems:
        print(f'  PROBLEM: {p}', file=sys.stderr)
sys.exit(0 if ok else 1)
"

echo "=== Campaign A complete ==="
