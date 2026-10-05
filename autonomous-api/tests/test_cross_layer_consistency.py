"""Tests for Bucket 3.9 cross-layer architectural consistency."""

import pytest

from app.engine.cross_layer_consistency import (
    CrossLayerConsistencyEngine,
    LayerArtifact,
)


def test_consistent_cross_layer_model():
    engine = CrossLayerConsistencyEngine(
        project_id="p1",
        artifacts=[
            LayerArtifact("REQ-1", "requirement"),
            LayerArtifact("CON-1", "contract", requirement_ids=("REQ-1",)),
            LayerArtifact("API-1", "api", requirement_ids=("REQ-1",), contract_ids=("CON-1",)),
            LayerArtifact("BE-1", "backend", requirement_ids=("REQ-1",), contract_ids=("CON-1",)),
            LayerArtifact("FE-1", "frontend", requirement_ids=("REQ-1",), contract_ids=("CON-1",)),
            LayerArtifact("T-1", "test", requirement_ids=("REQ-1",), verification_ids=("V-1",)),
        ],
    )

    report = engine.inspect()
    assert report.consistent
    assert report.findings == ()
    assert len(report.digest) == 64


def test_orphan_and_missing_links_are_blocking():
    report = CrossLayerConsistencyEngine(
        project_id="p1",
        artifacts=[
            LayerArtifact("API-1", "api"),
            LayerArtifact("BE-1", "backend", requirement_ids=("REQ-MISSING",), contract_ids=("CON-MISSING",)),
        ],
    ).inspect()

    kinds = {finding.kind for finding in report.findings}
    assert "orphan-requirement-trace" in kinds
    assert "missing-requirement" in kinds
    assert "missing-contract" in kinds
    assert not report.consistent


def test_invalid_requirement_and_contract_targets_are_detected():
    report = CrossLayerConsistencyEngine(
        project_id="p1",
        artifacts=[
            LayerArtifact("REQ-1", "requirement"),
            LayerArtifact("API-1", "api", requirement_ids=("API-2",), contract_ids=("API-3",)),
            LayerArtifact("API-2", "api"),
            LayerArtifact("API-3", "api"),
        ],
    ).inspect()

    kinds = {finding.kind for finding in report.findings}
    assert "invalid-requirement-target" in kinds
    assert "invalid-contract-target" in kinds


def test_untraced_test_is_detected():
    report = CrossLayerConsistencyEngine(
        project_id="p1",
        artifacts=[LayerArtifact("T-1", "test")],
    ).inspect()

    assert any(f.kind == "untraced-verification" for f in report.findings)


def test_duplicate_artifacts_fail_closed():
    with pytest.raises(ValueError, match="duplicate-artifact-id"):
        CrossLayerConsistencyEngine(
            project_id="p1",
            artifacts=[
                LayerArtifact("A", "architecture"),
                LayerArtifact("A", "backend"),
            ],
        )


def test_report_digest_is_deterministic():
    artifacts = [
        LayerArtifact("REQ-1", "requirement"),
        LayerArtifact("CON-1", "contract", requirement_ids=("REQ-1",)),
        LayerArtifact("API-1", "api", requirement_ids=("REQ-1",), contract_ids=("CON-1",)),
    ]
    first = CrossLayerConsistencyEngine(project_id="p1", artifacts=artifacts).inspect()
    second = CrossLayerConsistencyEngine(project_id="p1", artifacts=reversed(artifacts)).inspect()

    assert first == second
