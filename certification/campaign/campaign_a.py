"""Campaign A — substrate validation: 39 workloads × 2 backends."""
from __future__ import annotations
import json
import os
from certification.corpus.corpus import default_corpus, corpus_hash, classify_novelty
from certification.evidence.ledger import EvidenceLedger
from certification.campaign.runner import CampaignRunner, CampaignAggregator
from certification.campaign.plan_builder import build_artifacts_for
from compiler.composition import build_backend_registry


BACKENDS = ["python-fastapi", "rust-axum"]
DEFAULT_LEDGER = "release/evidence/cbc1-a-ledger.jsonl"
DEFAULT_AGGREGATE = "release/evidence/cbc1-a-aggregate.json"


def run_campaign_a(
    ledger_path: str = DEFAULT_LEDGER,
    out_path: str = DEFAULT_AGGREGATE,
) -> tuple[list, dict]:
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    reg = build_backend_registry()
    ledger = EvidenceLedger(ledger_path)
    runner = CampaignRunner()
    aggregator = CampaignAggregator()

    corpus = default_corpus()
    ch = corpus_hash()
    seen_intents: set[str] = set()
    seen_archs: set[str] = set()
    trials = []
    for w in corpus:
        novelty = classify_novelty(w, seen_intents, seen_archs)
        seen_intents.add(w.intent)
        seen_archs.add(w.intent)
        artifacts = build_artifacts_for(w)
        for bn in BACKENDS:
            trial = runner.run_trial(
                intent=w.intent,
                category=w.category.value,
                novelty_class=novelty.value,
                plan=artifacts.plan,
                revision_id=artifacts.revision.revision_id,
                backend=reg.get(bn),
                corpus_hash=ch,
                requirement_graph_hash=artifacts.requirement_graph_hash,
                genome_hash=artifacts.genome_hash,
                workload=w,
                artifacts=artifacts,
            )
            ledger.append(trial.model_dump())
            aggregator.add(trial)
            trials.append(trial)

    summary = aggregator.summary()
    summary["corpus_hash"] = ch
    summary["corpus_size"] = len(corpus)
    summary["total_trials"] = len(trials)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    assert EvidenceLedger.verify(ledger_path), "Evidence chain broken"
    return trials, summary
