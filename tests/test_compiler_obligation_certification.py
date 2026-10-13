"""Tests for the cross-pipeline obligation evidence assembly gate."""
from tiannara.application.compiler.obligation_certification import (
    assemble_obligation_certification,
)
from tiannara.application.compiler.obligation_evidence import ObligationEvidenceVerdict
from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    EnforcementPoint,
    Strength,
)

SOURCE_HASH = "a" * 64


def record(obligation_id="auth.workspace_scope", **overrides):
    values = {
        "schema_version": "1.0",
        "obligation_id": obligation_id,
        "source_graph_id": "taskflow-v1",
        "source_graph_hash": SOURCE_HASH,
        "domain": "authorization",
        "statement": "Workspace reads must be scoped to the authenticated member.",
        "applicability": Applicability.REQUIRED,
        "required_strength": Strength.MUST,
        "consumer_binding": "fastapi-runtime@1",
        "enforcement_points": (
            EnforcementPoint(kind="repository", locator="app/repositories/workspaces.py"),
        ),
        "acceptance_scenarios": (),
        "disposition": Disposition.UNKNOWN,
    }
    values.update(overrides)
    return CompilerObligationRecord(**values)


def verdict(disposition=Disposition.PASS, *, ok=None, blockers=()):
    if ok is None:
        ok = disposition is Disposition.PASS and not blockers
    return ObligationEvidenceVerdict(
        disposition=disposition,
        verified_scenarios=("cross-workspace-read-denied",) if ok else (),
        missing_scenarios=(),
        invalid_evidence_refs=(),
        blockers=tuple(blockers),
    )


def assemble(evaluations, required=("auth.workspace_scope",), source_hash=SOURCE_HASH):
    return assemble_obligation_certification(
        evaluations,
        expected_source_graph_hash=source_hash,
        required_obligation_ids=required,
    )


def test_all_required_obligations_need_verified_pass():
    result = assemble(((record(), verdict()),))
    assert result.disposition is Disposition.PASS
    assert result.ok
    assert result.passed_obligations == ("auth.workspace_scope",)


def test_missing_required_record_is_unknown():
    result = assemble((), required=("auth.workspace_scope", "auth.foreign_delete"))
    assert result.disposition is Disposition.UNKNOWN
    assert result.unknown_obligations == ("auth.foreign_delete", "auth.workspace_scope")
    assert not result.ok


def test_duplicate_record_blocks_certification():
    item = record()
    result = assemble(((item, verdict()), (item, verdict())))
    assert result.disposition is Disposition.UNKNOWN
    assert any("duplicate obligation" in blocker for blocker in result.blockers)


def test_stale_source_graph_cannot_pass():
    result = assemble(((record(), verdict()),), source_hash="b" * 64)
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok


def test_observed_failure_is_preserved():
    result = assemble(((record(), verdict(Disposition.FAIL)),))
    assert result.disposition is Disposition.FAIL
    assert result.failed_obligations == ("auth.workspace_scope",)


def test_blocked_consumer_cannot_pass():
    result = assemble(((record(), verdict(Disposition.BLOCKED_NO_CONSUMER)),))
    assert result.disposition is Disposition.BLOCKED_UNRESOLVED
    assert result.blocked_obligations == ("auth.workspace_scope",)


def test_pass_with_verifier_blockers_cannot_pass():
    result = assemble(((record(), verdict(Disposition.PASS, ok=False, blockers=("missing evidence",)),))
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok


def test_empty_suite_cannot_be_certified():
    result = assemble((), required=())
    assert result.disposition is Disposition.UNKNOWN
    assert not result.ok
