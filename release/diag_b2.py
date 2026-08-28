"""Diagnose NOT_CERTIFIED trials in the B2 ledger."""
import json

records = [json.loads(l)["trial"] for l in open("release/evidence/cbc1-b-B2-ledger.jsonl") if l.strip()]
for t in records:
    if t.get("verdict") != "CERTIFIED":
        print(f"trial_id={t['trial_id'][:8]} backend={t['backend']} intent={t['intent'][:40]}")
        for s in t.get("stages", []):
            if not s.get("passed"):
                print(f"  stage={s['stage']} mode={s.get('mode')} detail={s.get('detail','')[:200]}")
        print()