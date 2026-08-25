"""Evidence subsystem write acceptance: E-1..E-3."""
from __future__ import annotations

import pytest

from app.core.evidence.commands import StoreEvidence
from app.core.evidence.invariants import EvidenceInvariantError
from app.core.ids import content_hash
from app.evidence.adapters.memory import InMemoryEvidenceStore
from app.evidence.subsystem import EvidenceSubsystem


def _subsystem():
    store = InMemoryEvidenceStore()
    return EvidenceSubsystem(store=store), store


@pytest.mark.asyncio
async def test_e1_content_hash_computed_at_write():
    evidence, _ = _subsystem()
    artifact = "verification-artifact"
    result = await evidence.store(StoreEvidence(
        evidenceId="ev-1", evidenceType="verification",
        producedBy="qa-agent", artifact=artifact, summary="passed",
    ))
    assert result.contentHash == content_hash(artifact)
    assert len(result.contentHash) == 64


@pytest.mark.asyncio
async def test_e2_evidence_is_immutable():
    evidence, _ = _subsystem()
    await evidence.store(StoreEvidence(
        evidenceId="ev-1", evidenceType="verification",
        producedBy="qa", artifact=b"data", summary="s",
    ))
    with pytest.raises(EvidenceInvariantError, match="E-2"):
        await evidence.store(StoreEvidence(
            evidenceId="ev-1", evidenceType="verification",
            producedBy="qa", artifact=b"tampered", summary="s2",
        ))


@pytest.mark.asyncio
async def test_e3_existence_check_supported():
    evidence, _ = _subsystem()
    # E-3 is enforced by the REFERENCING subsystems; this verifies the
    # Evidence subsystem exposes the existence check they use.
    assert await evidence.exists("missing") is False
    await evidence.store(StoreEvidence(
        evidenceId="ev-2", evidenceType="certification",
        producedBy="certifier", artifact="cert", summary="granted",
    ))
    assert await evidence.exists("ev-2") is True


@pytest.mark.asyncio
async def test_evidence_retrievable_after_store():
    evidence, _ = _subsystem()
    await evidence.store(StoreEvidence(
        evidenceId="ev-3", evidenceType="test", producedBy="tester",
        artifact="artifact-3", summary="summary-3",
    ))
    record = await evidence.get("ev-3")
    assert record["evidenceId"] == "ev-3"
    assert record["summary"] == "summary-3"
    assert len(record["contentHash"]) == 64