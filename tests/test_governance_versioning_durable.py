"""Durable ConstitutionVersionRepository -- file-backed persistence for the
constitutional version chain, implementing the same Protocol semantics as the
reference InMemoryConstitutionVersionRepository (add/replace/get/all) with
atomic writes. The adapter is a drop-in swap for any caller currently
constructing ``InMemoryConstitutionVersionRepository``, making the ratified
version chain (and therefore ``constitutional_currency`` and
``audit_integrity``) durable across process restarts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from constitutional_architecture.governance.schemas import (
    ChangeKind,
    ConstitutionVersionISR,
    VersionStatus,
)
from constitutional_architecture.governance.versioning import (
    FileBackedConstitutionVersionRepository,
    VersioningError,
    VersionManager,
)

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _version(version_id: str, semver: str = "1.0.0") -> ConstitutionVersionISR:
    return ConstitutionVersionISR(
        version_id=version_id,
        semver=semver,
        status=VersionStatus.PROPOSED,
        policy_set_ref="pset:1.0.0",
        proposed_by="tester",
        proposed_at=_NOW,
    )


def _ratify_outcome():
    return SimpleNamespace(approved=True, workflow_ref="workflow:test")


def test_protocol_contract_add_get_all(tmp_path):
    repo = FileBackedConstitutionVersionRepository(tmp_path)
    v = _version("cv-1")
    repo.add(v)
    assert repo.get("cv-1") == v
    assert len(repo.all()) == 1


def test_add_rejects_duplicate(tmp_path):
    repo = FileBackedConstitutionVersionRepository(tmp_path)
    repo.add(_version("cv-1"))
    with pytest.raises(VersioningError, match="duplicate_version_id"):
        repo.add(_version("cv-1"))


def test_replace_unknown_raises_and_update_persists(tmp_path):
    repo = FileBackedConstitutionVersionRepository(tmp_path)
    with pytest.raises(VersioningError, match="unknown_version_id"):
        repo.replace(_version("nope", semver="9.9.9"))
    repo.add(_version("cv-1"))
    ratified = _version("cv-1").model_copy(update={
        "status": VersionStatus.RATIFIED,
        "effective_at": _NOW,
        "ratification_workflow_ref": "wf",
        "lineage_ref": "cl-1",
    })
    repo.replace(ratified)
    assert repo.get("cv-1").status is VersionStatus.RATIFIED


def test_persistence_across_instances(tmp_path):
    repo = FileBackedConstitutionVersionRepository(tmp_path)
    v = _version("cv-1")
    repo.add(v)
    # A brand-new repository pointed at the same file reads what was written.
    again = FileBackedConstitutionVersionRepository(tmp_path)
    assert again.get("cv-1") == v
    assert len(again.all()) == 1


def test_version_manager_end_to_end_persists_ratified_chain(tmp_path):
    repo = FileBackedConstitutionVersionRepository(tmp_path)
    manager = VersionManager(repo, evidence=None)
    proposed = manager.propose(
        semver="1.0.0", policy_set_ref="pset:1.0.0",
        proposed_by="tester", change_kind=ChangeKind.AMENDMENT,
        summary="init", now=_NOW,
    )
    assert proposed.status is VersionStatus.PROPOSED
    ratified = manager.ratify(
        version_id=proposed.version_id, outcome=_ratify_outcome(), now=_NOW,
    )
    assert ratified.status is VersionStatus.RATIFIED
    assert ratified.ratification_workflow_ref == "workflow:test"

    # The ratified head is durable: a fresh manager reads it from the file.
    again = FileBackedConstitutionVersionRepository(tmp_path)
    versions = VersionManager(again).history()
    assert len(versions) == 1
    assert versions[0].status is VersionStatus.RATIFIED

    # The version chain is human-auditable JSON on disk.
    raw = json.loads((tmp_path / "constitution_versions.json").read_text())
    assert next(iter(raw)).startswith("cv-")
