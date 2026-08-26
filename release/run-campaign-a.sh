#!/usr/bin/env bash
#
# run-campaign-a.sh — Campaign A behavioral run (39 workloads × 2 backends = 78 trials).
# Produces evidence ledger + aggregate.

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
from certification.corpus.corpus import default_corpus, corpus_hash
import sys
path = 'release/evidence/cbc1-a-ledger.jsonl'
ok = EvidenceLedger.verify(path)
count = EvidenceLedger.count(path)
expected = len(default_corpus()) * 2
print(f'Ledger: {count}/{expected} records, chain_valid={ok}')
sys.exit(0 if ok and count == expected else 1)
"

echo "=== Campaign A complete ==="
