#!/usr/bin/env bash
#
# run-campaign-a.sh — Campaign A behavioral run (13 categories × 2 backends).
# Produces evidence ledger + aggregate.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/release/evidence"

echo "=== Campaign A: 13 categories × 2 backends ==="

cd "$REPO_ROOT"
python -m certification.campaign.campaign_a

echo "=== Verifying evidence ledger ==="
python -c "
from certification.evidence.ledger import EvidenceLedger
import sys
path = 'release/evidence/cbc1-a-ledger.jsonl'
ok = EvidenceLedger.verify(path)
count = EvidenceLedger.count(path)
print(f'Ledger: {count} records, chain_valid={ok}')
sys.exit(0 if ok else 1)
"

echo "=== Campaign A complete ==="
