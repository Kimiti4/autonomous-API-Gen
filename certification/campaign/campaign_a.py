"""Campaign A — substrate validation: 13 categories × 2 backends."""
from __future__ import annotations
import json
import os
from certification.corpus.corpus import default_corpus
from certification.evidence.ledger import EvidenceLedger
from certification.campaign.runner import CampaignRunner, CampaignAggregator
from certification.campaign.plan_builder import build_plan_for
from compiler.composition import build_backend_registry


BACKENDS = ["python-fastapi", "rust-axum"]
DEFAULT_LEDGER = "release/evidence/cbc1-a-ledger.jsonl"
DEFAULT_AGGREGATE = "release/evidence/cbc1-a-aggregate.json"


def run_campaign_a(
    ledger_path: str = DEFAULT_LEDGER,
    out_path: str = DEFAULT_AGGREGATE,
) -> tuple[list, dict]:
    """Run Campaign A: all 13 categories × 2 backends with stub stages."""
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    reg = build_backend_registry()
    ledger = EvidenceLedger(ledger_path)
    runner = CampaignRunner()
    aggregator = CampaignAggregator()

    corpus = default_corpus()
    trials = []
    for w in corpus:
        for bn in BACKENDS:
            plan, revision = build_plan_for(w.intent, w.category.value, w.seeds)
            trial = runner.run_trial(
                intent=w.intent,
                category=w.category.value,
                novelty_class="template",
                plan=plan,
                revision_id=revision.revision_id,
                backend=reg.get(bn),
            )
            ledger.append(trial.model_dump())
            aggregator.add(trial)
            trials.append(trial)

    summary = aggregator.summary()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    assert EvidenceLedger.verify(ledger_path), "Evidence chain broken"
    return trials, summary
