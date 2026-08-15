"""Phase 28 - VersionManager invariant verification."""

from datetime import datetime, timezone

import pytest

from constitutional_architecture.governance.audit import AuditEvidenceRecorder
from constitutional_architecture.governance.versioning import (
    InMemoryConstitutionVersionRepository,
    VersioningError,
    VersionManager,
    parse_semver,
)
from constitutional_architecture.governance.schemas import ChangeKind, VersionStatus
from constitutional_architecture.governance.voting import VoteOutcome

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def make_manager():
    recorder = AuditEvidenceRecorder()
    manager = VersionManager(InMemoryConstitutionVersionRepository(), evidence=recorder)
    return manager, recorder


def outcome(approved: bool = True, workflow_ref: str = "wf-1") -> VoteOutcome:
    return VoteOutcome(workflow_ref=workflow_ref, approved=approved,
                       decided_at=NOW, reason="test")


def propose(manager, semver="1.0.0"):
    return manager.propose(semver=semver, policy_set_ref="ps-1", proposed_by="architect",
                           change_kind=ChangeKind.AMENDMENT, summary="s", now=NOW)


def test_semver_parser_rejects_garbage():
    with pytest.raises(VersioningError):
        parse_semver("1.0")


def test_propose_ratify_lifecycle():
    manager, recorder = make_manager()
    v1 = propose(manager)
    assert v1.status is VersionStatus.PROPOSED and v1.predecessor_ref is None

    ratified = manager.ratify(version_id=v1.version_id, outcome=outcome(), now=NOW)
    assert ratified.status is VersionStatus.RATIFIED
    assert ratified.ratification_workflow_ref == "wf-1"
    assert ratified.effective_at == NOW
    assert manager.current().version_id == v1.version_id

    lineage = manager.lineage()
    assert len(lineage) == 1
    assert lineage[0].authorizing_workflow_ref == "wf-1"
    assert lineage[0].parent_version_refs == []
    assert ratified.lineage_ref == lineage[0].lineage_id
    assert recorder.verify_chain()


def test_ratification_requires_approved_vote():
    manager, _ = make_manager()
    v1 = propose(manager)
    with pytest.raises(VersioningError, match="approved_vote"):
        manager.ratify(version_id=v1.version_id, outcome=outcome(approved=False), now=NOW)


def test_semver_must_strictly_increase():
    manager, _ = make_manager()
    propose(manager, "1.0.0")
    with pytest.raises(VersioningError, match="strictly_increase"):
        propose(manager, "1.0.0")
    with pytest.raises(VersioningError, match="strictly_increase"):
        propose(manager, "0.9.9")


def test_ratified_head_supersedes_predecessor():
    manager, _ = make_manager()
    v1 = propose(manager, "1.0.0")
    manager.ratify(version_id=v1.version_id, outcome=outcome(), now=NOW)
    v2 = propose(manager, "1.1.0")
    assert v2.predecessor_ref == v1.version_id
    manager.ratify(version_id=v2.version_id, outcome=outcome(), now=NOW)

    assert manager.current().version_id == v2.version_id
    statuses = {v.version_id: v.status for v in manager.history()}
    assert statuses[v1.version_id] is VersionStatus.SUPERSEDED
    assert statuses[v2.version_id] is VersionStatus.RATIFIED


def test_double_ratification_rejected():
    manager, _ = make_manager()
    v1 = propose(manager)
    manager.ratify(version_id=v1.version_id, outcome=outcome(), now=NOW)
    with pytest.raises(VersioningError, match="only_proposed"):
        manager.ratify(version_id=v1.version_id, outcome=outcome(), now=NOW)


def test_unknown_version_ratification_rejected():
    manager, _ = make_manager()
    with pytest.raises(VersioningError, match="unknown_version_id"):
        manager.ratify(version_id="cv-ghost", outcome=outcome(), now=NOW)
