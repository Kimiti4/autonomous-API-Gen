"""CBC-1 Campaign A gates — runnability, ledger, metrics, campaign A (78 trials)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

import pytest

from compiler.core.lowering import isr_to_plan
from compiler.core.conformance import CHECKER, plan_element_ids
from compiler.core.repository import build_repository
from compiler.composition import build_backend_registry
from certification.campaign.plan_builder import build_plan_for
from certification.campaign.runner import CampaignRunner, CampaignAggregator
from certification.campaign.campaign_a import run_campaign_a
from certification.core.trial import Trial, TrialStage, TrialMetrics, compose_verdict
from certification.core.metrics import compute
from certification.corpus.corpus import Category, Workload, default_corpus, corpus_hash
from certification.evidence.ledger import EvidenceLedger, GENESIS_HASH
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _revision() -> ISRRevision:
    g = ISRGraph(
        nodes={
            "service:a": Node(id="service:a", type=NodeType.SERVICE, properties={"label": "orders"}),
            "dm:core": Node(id="dm:core", type=NodeType.DATA_MODEL, properties={"label": "Order"}),
            "event:e": Node(id="event:e", type=NodeType.EVENT, properties={"label": "OrderCreated"}),
            "sec:p": Node(id="sec:p", type=NodeType.SECURITY_POLICY),
        },
        edges={
            "pers": Edge(id="pers", type=EdgeType.PERSISTS, source_id="service:a", target_id="dm:core"),
            "pub": Edge(id="pub", type=EdgeType.PUBLISHES, source_id="service:a", target_id="event:e"),
            "sec": Edge(id="sec", type=EdgeType.SECURED_BY, source_id="service:a", target_id="sec:p"),
        },
    )
    return ISRRevision.create("test", "rev", "1.0", g, Provenance(created_by="test", created_at="2025-01-01T00:00:00Z"))


# ---------------------------------------------------------------------------
# Runnability — Python backend emits runnable app
# ---------------------------------------------------------------------------

def test_python_backend_emits_health_endpoint():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    assert "app/main.py" in repo.files
    assert "@app.get('/health')" in repo.files["app/main.py"]
    assert "return {'status': 'ok'}" in repo.files["app/main.py"]


def test_python_backend_emits_requirements():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    assert "requirements.txt" in repo.files
    assert "fastapi" in repo.files["requirements.txt"]


def test_python_backend_emits_test():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    assert "tests/test_app.py" in repo.files
    assert "test_health" in repo.files["tests/test_app.py"]


def test_python_backend_emits_dockerfile():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    assert "Dockerfile" in repo.files
    assert "uvicorn" in repo.files["Dockerfile"]


def test_python_backend_emits_domain_models():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    domain_files = [p for p in repo.files if p.startswith("app/domain/")]
    assert len(domain_files) >= 1
    assert "BaseModel" in repo.files[domain_files[0]]


def test_python_backend_conforms():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)
    report = backend.conformance(plan, repo)
    assert report.passed
    assert report.missing == []


# ---------------------------------------------------------------------------
# Runnability — Rust backend emits runnable app
# ---------------------------------------------------------------------------

def test_rust_backend_emits_health_endpoint():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)
    assert "src/main.rs" in repo.files
    assert "/health" in repo.files["src/main.rs"]
    assert "async fn health" in repo.files["src/main.rs"]


def test_rust_backend_emits_cargo_toml():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)
    assert "Cargo.toml" in repo.files
    assert "axum" in repo.files["Cargo.toml"]
    assert "tokio" in repo.files["Cargo.toml"]


def test_rust_backend_emits_dockerfile():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)
    assert "Dockerfile" in repo.files
    assert "cargo build --release" in repo.files["Dockerfile"]


def test_rust_backend_emits_test():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)
    assert "#[cfg(test)]" in repo.files["src/main.rs"]
    assert "#[test]" in repo.files["src/main.rs"]


def test_rust_backend_conforms():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)
    report = backend.conformance(plan, repo)
    assert report.passed
    assert report.missing == []


# ---------------------------------------------------------------------------
# Plan builder — deterministic from workload
# ---------------------------------------------------------------------------

def test_plan_builder_deterministic():
    w = default_corpus()[0]
    p1, r1, rg1, g1 = build_plan_for(w)
    p2, r2, rg2, g2 = build_plan_for(w)
    assert p1.model_dump_json() == p2.model_dump_json()
    assert r1.content_hash == r2.content_hash
    assert rg1 == rg2 and g1 == g2


def test_plan_builder_different_workloads():
    w1 = default_corpus()[0]
    w2 = default_corpus()[-1]
    p1, _, _, _ = build_plan_for(w1)
    p2, _, _, _ = build_plan_for(w2)
    assert p1.plan_id != p2.plan_id


# ---------------------------------------------------------------------------
# Evidence ledger — append-only hash chain
# ---------------------------------------------------------------------------

def test_ledger_append_and_verify():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "ledger.jsonl")
    ledger = EvidenceLedger(path)

    t1 = {"trial_id": "t1", "verdict": "CERTIFIED"}
    h1 = ledger.append(t1)
    assert len(h1) == 64

    t2 = {"trial_id": "t2", "verdict": "NOT_CERTIFIED"}
    h2 = ledger.append(t2)
    assert h2 != h1

    assert EvidenceLedger.verify(path)


def test_ledger_detects_tampering():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "ledger.jsonl")
    ledger = EvidenceLedger(path)
    ledger.append({"trial_id": "t1"})
    ledger.append({"trial_id": "t2"})

    with open(path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            if '"t2"' in line:
                f.write(line.replace('"t2"', '"TAMPERED"'))
            else:
                f.write(line)

    assert not EvidenceLedger.verify(path)


def test_ledger_count():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "ledger.jsonl")
    ledger = EvidenceLedger(path)
    ledger.append({"a": 1})
    ledger.append({"a": 2})
    ledger.append({"a": 3})
    assert EvidenceLedger.count(path) == 3


def test_ledger_genesis_hash():
    assert GENESIS_HASH == "0" * 64
    assert len(GENESIS_HASH) == 64


# ---------------------------------------------------------------------------
# Metrics — expanded engineering-quality signals
# ---------------------------------------------------------------------------

def test_metrics_richer_engineering_quality():
    files = {
        "app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "app/service.py": "class S:\n    pass\n",
        "README.md": "# Test\n",
    }
    m = compute(
        repo_files_count=3,
        stages={s: True for s in TrialStage},
        structural_passed=True,
        test_passed=True,
        runtime_passed=True,
        repo_content_hash="abc",
        files=files,
    )
    assert "lint_score" in m.engineering_quality
    assert "complexity" in m.engineering_quality
    assert "maintainability" in m.engineering_quality
    assert "documentation_completeness" in m.engineering_quality
    assert m.engineering_quality["lint_score"] == 1.0
    assert m.engineering_quality["documentation_completeness"] == 0.5


def test_metrics_lint_penalises_bare_except():
    files = {"bad.py": "try:\n    pass\nexcept:\n    pass\n"}
    m = compute(
        repo_files_count=1,
        stages={s: True for s in TrialStage},
        structural_passed=True,
        test_passed=True,
        runtime_passed=True,
        files=files,
    )
    assert m.engineering_quality["lint_score"] < 1.0


def test_metrics_complexity_counts_branches():
    files = {"code.py": "if True:\n    for i in range(10):\n        while False:\n            pass\n"}
    m = compute(
        repo_files_count=1,
        stages={s: True for s in TrialStage},
        structural_passed=True,
        test_passed=True,
        runtime_passed=True,
        files=files,
    )
    assert m.engineering_quality["complexity"] >= 3


# ---------------------------------------------------------------------------
# Campaign A — full orchestrator (39 workloads × 2 backends = 78 trials)
# ---------------------------------------------------------------------------

def test_campaign_a_runs_all_categories():
    d = tempfile.mkdtemp()
    ledger_path = os.path.join(d, "ledger.jsonl")
    agg_path = os.path.join(d, "aggregate.json")
    trials, summary = run_campaign_a(ledger_path, agg_path)
    assert len(trials) == 78
    assert summary["total"] == 78
    assert summary["corpus_size"] == 39
    assert summary["total_trials"] == 78
    assert summary["certified"] == 78
    assert summary["success_rate"] == 1.0
    assert EvidenceLedger.verify(ledger_path)
    assert EvidenceLedger.count(ledger_path) == 78


def test_campaign_a_success_matrix():
    d = tempfile.mkdtemp()
    _, summary = run_campaign_a(
        os.path.join(d, "ledger.jsonl"),
        os.path.join(d, "agg.json"),
    )
    matrix = summary["success_matrix"]
    assert "crud_saas" in matrix
    assert "banking" in matrix
    assert "streaming" in matrix
    for cat in matrix:
        assert "novel_intent" in matrix[cat]


def test_campaign_a_failure_taxonomy_empty():
    d = tempfile.mkdtemp()
    _, summary = run_campaign_a(
        os.path.join(d, "ledger.jsonl"),
        os.path.join(d, "agg.json"),
    )
    assert summary["failure_taxonomy"] == {}


def test_campaign_a_corpus_hash_recorded():
    d = tempfile.mkdtemp()
    _, summary = run_campaign_a(
        os.path.join(d, "ledger.jsonl"),
        os.path.join(d, "agg.json"),
    )
    assert summary["corpus_hash"] == corpus_hash()
    assert len(summary["corpus_hash"]) == 64
