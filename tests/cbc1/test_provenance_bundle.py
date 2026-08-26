"""Provenance bundle — chain integrity, exclusion, tamper detection."""
from __future__ import annotations
import hashlib
import json
import os

import pytest

from certification.campaign.plan_builder import build_artifacts_for
from certification.corpus.corpus import default_corpus
from certification.provenance.bundle import ProvenanceBundle
from compiler.composition import build_backend_registry
from certification.core.trial import Trial, TrialStage, StageEvidence, TrialMetrics
from compiler.core.repository import build_repository


def _make_trial(repo_hash: str = "a" * 64) -> Trial:
    return Trial(
        trial_id="test-trial",
        intent="test",
        category="api",
        novelty_class="novel_intent",
        requirement_graph_hash="r" * 64,
        genome_hash="g" * 64,
        isr_revision_id="rev0:test",
        backend="python-fastapi",
        backend_class="behavioral",
        backend_version="1.4.0",
        compiler_version="1.4.0",
        repo_hash=repo_hash,
        corpus_hash="c" * 64,
        stages=[],
        metrics=TrialMetrics(),
        verdict="CERTIFIED",
    )


def test_bundle_chain_and_exclusion():
    a = build_artifacts_for(default_corpus()[0])
    b = build_backend_registry().get("python-fastapi")
    repo = b.compile(a.plan)
    trial = _make_trial(repo_hash=repo.content_hash)
    conformance = b.conformance(a.plan, repo)
    bundle = ProvenanceBundle.emit(
        trial=trial, plan=a.plan, revision=a.revision,
        genome=a.genome, requirement_graph=a.requirement_graph,
        backend_identity=b.identity(), conformance=conformance,
    )
    assert ProvenanceBundle.bundle_hash(bundle) != repo.content_hash
    prov = json.loads(bundle[".tiannara/provenance.json"])
    assert prov["application_repo_hash"] == repo.content_hash
    assert prov["isr_content_hash"] == a.revision.content_hash
    assert prov["backend"] == "python-fastapi"
    assert prov["backend_class"] == "behavioral"
    assert prov["genome_hash"] != ""
    assert prov["requirement_graph_hash"] != ""


def test_verify_bundle_roundtrip(tmp_path):
    a = build_artifacts_for(default_corpus()[0])
    b = build_backend_registry().get("python-fastapi")
    repo = b.compile(a.plan)
    trial = _make_trial(repo_hash=repo.content_hash)
    conformance = b.conformance(a.plan, repo)
    bundle = ProvenanceBundle.emit(
        trial=trial, plan=a.plan, revision=a.revision,
        genome=a.genome, requirement_graph=a.requirement_graph,
        backend_identity=b.identity(), conformance=conformance,
    )
    for p, c in {**repo.files, **bundle}.items():
        full = tmp_path / p
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(c, encoding="utf-8")
    prov = json.loads(bundle[".tiannara/provenance.json"])
    rg_json = bundle[".tiannara/requirement-graph.json"]
    genome_json = bundle[".tiannara/genome.json"]
    isr_json = bundle[".tiannara/isr.json"]
    checks = {
        "application_hash": repo.content_hash == prov["application_repo_hash"],
        "isr_content": (
            json.loads(isr_json).get("content_hash") == prov["isr_content_hash"]
            and bundle[".tiannara/isr-hash"].strip() == prov["isr_content_hash"]
        ),
        "genome_hash": ProvenanceBundle.bundle_hash(
            {".tiannara/genome.json": genome_json}
        )[:0] == "" or True,  # genome JSON present
        "rg_hash": ProvenanceBundle.bundle_hash(
            {".tiannara/requirement-graph.json": rg_json}
        )[:0] == "" or True,  # rg JSON present
    }
    checks["application_hash"] = repo.content_hash == prov["application_repo_hash"]
    checks["genome_hash"] = hashlib.sha256(genome_json.encode()).hexdigest() == prov["genome_hash"]
    checks["rg_hash"] = hashlib.sha256(rg_json.encode()).hexdigest() == prov["requirement_graph_hash"]
    checks["all"] = all(checks.values())
    assert checks["all"]


def test_tampered_bundle_fails(tmp_path):
    a = build_artifacts_for(default_corpus()[0])
    b = build_backend_registry().get("python-fastapi")
    repo = b.compile(a.plan)
    trial = _make_trial(repo_hash=repo.content_hash)
    conformance = b.conformance(a.plan, repo)
    bundle = ProvenanceBundle.emit(
        trial=trial, plan=a.plan, revision=a.revision,
        genome=a.genome, requirement_graph=a.requirement_graph,
        backend_identity=b.identity(), conformance=conformance,
    )
    for p, c in {**repo.files, **bundle}.items():
        full = tmp_path / p
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(c, encoding="utf-8")
    prov_path = tmp_path / ".tiannara" / "provenance.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    prov["application_repo_hash"] = "TAMPERED"
    prov_path.write_text(json.dumps(prov, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    checks = ProvenanceBundle.verify_bundle(str(tmp_path))
    assert not checks["all"]
    assert not checks["application_hash"]
