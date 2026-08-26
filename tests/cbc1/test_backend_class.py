"""Backend class enforcement — stubs never certify, verifier catches forgeries."""
from __future__ import annotations
import json

import pytest

from compiler.core.protocol import (
    BackendClass, BackendIdentity, eligible_for_behavioral_certification,
)
from certification.campaign.verify_campaign import verify_campaign


class StubBackend:
    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name="stub", language="x", framework="y",
            version="0", backend_class=BackendClass.STUB,
        )


class StructuralBackend:
    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name="structural", language="x", framework="y",
            version="0", backend_class=BackendClass.STRUCTURAL,
        )


def test_stub_never_eligible():
    assert not eligible_for_behavioral_certification(StubBackend().identity())


def test_structural_never_eligible():
    assert not eligible_for_behavioral_certification(StructuralBackend().identity())


def test_reference_backends_are_behavioral():
    from compiler.composition import build_backend_registry
    reg = build_backend_registry()
    for name in ["python-fastapi", "rust-axum"]:
        b = reg.get(name)
        assert eligible_for_behavioral_certification(b.identity())


def test_verifier_rejects_forged_certified_on_stub(tmp_path):
    from certification.evidence.ledger import EvidenceLedger, _canonical
    led = tmp_path / "l.jsonl"
    ledger = EvidenceLedger(str(led))
    t = {
        "trial_id": "t1", "intent": "i", "category": "banking",
        "novelty_class": "template",
        "requirement_graph_hash": "a", "genome_hash": "b",
        "isr_revision_id": "r", "backend": "stub",
        "backend_class": "stub", "backend_version": "0",
        "repo_hash": "h", "corpus_hash": "", "bundle_hash": "",
        "stages": [
            {"stage": "structural", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "semantic", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "build", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "test", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "deploy", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "runtime", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "destroy", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "verify", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
        ],
        "metrics": {}, "verdict": "CERTIFIED",
    }
    ledger.append(t)
    ok, _, _, problems = verify_campaign(str(led))
    assert not ok
    assert any("backend_class=stub" in p for p in problems)


def test_verifier_rejects_missing_stages(tmp_path):
    from certification.evidence.ledger import EvidenceLedger
    led = tmp_path / "l.jsonl"
    ledger = EvidenceLedger(str(led))
    t = {
        "trial_id": "t2", "intent": "i", "category": "api",
        "novelty_class": "novel_intent",
        "requirement_graph_hash": "a", "genome_hash": "b",
        "isr_revision_id": "r", "backend": "python-fastapi",
        "backend_class": "behavioral", "backend_version": "1.4.0",
        "repo_hash": "h", "corpus_hash": "", "bundle_hash": "",
        "stages": [
            {"stage": "structural", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
            {"stage": "semantic", "passed": True, "started_at": "",
             "completed_at": "", "logs_hash": "", "detail": ""},
        ],
        "metrics": {}, "verdict": "CERTIFIED",
    }
    ledger.append(t)
    ok, _, _, problems = verify_campaign(str(led))
    assert not ok
    assert any("missing stages" in p for p in problems)
