import json
from certification.evidence.ledger import EvidenceLedger
from certification.campaign.amplification import compute_amplification

ledger_path = "release/evidence/cbc1-b-B3-ledger.jsonl"
agg_path = "release/evidence/cbc1-b-B3-aggregate.json"
records = [json.loads(x) for x in open(ledger_path, encoding="utf-8") if x.strip()]
trials = [r.get("trial", r) for r in records]
certified = sum(1 for t in trials if t.get("verdict") == "CERTIFIED")
failed = len(trials) - certified
amp = compute_amplification(
    [t for t in trials if t.get("verdict") != "CERTIFIED"], certified
)
agg = {
    "wave": "B3",
    "scale_factor": 12,
    "declared_plan": {"expected_trials": 936, "planned_trials": 936},
    "wave_completed": False,
    "interrupted": True,
    "interrupt_reason": (
        "process crashed at N/936 with UnboundLocalError at campaign_b.py:538 "
        "(supplement_runs referenced in the planned-loop budget-exhausted early-return "
        "before it is bound); the final aggregate was never written. Ledger preserved "
        "immutable; relaunching fresh with the startup-polls/retry separation, build "
        "infra classifier, and the early-return crash fix."
    ),
    "total_trials": len(trials),
    "planned_trials": 936,
    "resumed_trials": 0,
    "supplement_trials": 0,
    "executed_trials": len(trials),
    "certified_trials": certified,
    "failed_trials": failed,
    "skipped_trials": 936 - len(trials),
    "certified": certified,
    "verdict": "NOT_CERTIFIED",
    "verdict_reason": "interrupted (not a certification verdict)",
    "amplification": {
        "infra_failures": amp.infrastructure_failures,
        "product_failures": amp.product_failures,
        "retry_executions": amp.retry_executions,
        "unexplained_retries": amp.unexplained_retries,
        "retry_rate": amp.retry_rate,
        "cascade_skips": amp.cascade_skipped,
    },
    "corpus_hash": "n/a (interrupted)",
}
with open(agg_path, "w", encoding="utf-8") as f:
    json.dump(agg, f, indent=2)
print(json.dumps(agg["amplification"]))