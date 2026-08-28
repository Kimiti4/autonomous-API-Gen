"""Check B2 ledger state."""
import json
import os

path = "release/evidence/cbc1-b-B2-ledger.jsonl"
if not os.path.exists(path):
    print("No B2 ledger found")
    exit(0)

with open(path) as f:
    records = [json.loads(l) for l in f if l.strip()]

total = len(records)
certified = sum(1 for r in records if r.get("verdict") == "CERTIFIED")
backends = {}
for r in records:
    b = r.get("backend", "?")
    backends[b] = backends.get(b, 0) + 1

print(f"B2 ledger: {total} trials, {certified} certified")
print(f"Backends: {backends}")
if records:
    last = records[-1]
    print(f"Last: backend={last.get('backend')} verdict={last.get('verdict')}")
