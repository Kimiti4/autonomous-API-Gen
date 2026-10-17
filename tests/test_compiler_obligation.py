"""Tests for the shared compiler-neutral obligation contract."""
from pydantic import ValidationError
import pytest

from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    EnforcementPoint,
    ScenarioEvidence,
    Strength,
)

HASH = "a" * 64


def base_record(**overrides):
    payload = {
        "schema_version": "1.0",
        "obligation_id": "auth.workspace_scope",
        "source_graph_id": "taskflow-v1",
        "source_graph_hash": HASH,
        "domain": "authorization",
        "statement": "All workspace reads and writes are scoped to the authenticated member.",
        "applicability": Applicability.REQUIRED,
        "required_strength": Strength.MUST,
    }
    payload.update(overrides)
    return payload


def passing_evidence():
    return ScenarioEvidence(
        scenario_id="cross-workspace-read-denied",
        outcome="PASS",
        evidence_ref="evidence://run/123/scenario/1",
        evidence_sha256="b" * 64,
        build_id="build-123",
        environment_fingerprint="python-3.12-linux",
    )


def test_unknown_is_default_and_obligation_hash_is_stable():
    first = CompilerObligationRecord(**base_record())
    second = CompilerObligationRecord(**base_record())
    assert first.disposition is Disposition.UNKNOWN
    assert first.obligation_hash == second.obligation_hash
    assert len(first.obligation_hash) == 64


def test_hash_changes_when_semantic_obligation_changes():
    first = CompilerObligationRecord(**base_record())
    changed = CompilerObligationRecord(
        **base_record(statement="Workspace membership is checked for each operation.")
    )
    assert first.obligation_hash != changed.obligation_hash


def test_stale_supplied_obligation_hash_is_rejected():
    with pytest.raises(ValidationError, match="obligation_hash"):
        CompilerObligationRecord(**base_record(obligation_hash="c" * 64))


def test_pass_requires_consumer_enforcement_point_and_passing_evidence():
    with pytest.raises(ValidationError, match="PASS requires"):
        CompilerObligationRecord(**base_record(disposition=Disposition.PASS))


def test_pass_accepts_source_bound_consumer_and_executed_evidence():
    record = CompilerObligationRecord(
        **base_record(
            consumer_binding="fastapi_hexagonal@adapter-v1",
            enforcement_points=(
                EnforcementPoint(
                    kind="repository",
                    locator="app/infrastructure/repositories.py:WorkspaceRepository",
                ),
            ),
            acceptance_scenarios=(passing_evidence(),),
            disposition=Disposition.PASS,
        )
    )
    assert record.disposition is Disposition.PASS
    assert record.obligation_hash == record.compute_hash()


def test_not_run_or_failed_scenario_cannot_support_pass():
    for outcome in ("NOT_RUN", "FAIL", "ERROR", "INCONCLUSIVE"):
        evidence = passing_evidence().model_copy(update={"outcome": outcome})
        with pytest.raises(ValidationError, match="every listed scenario to pass"):
            CompilerObligationRecord(
                **base_record(
                    consumer_binding="backend@v1",
                    enforcement_points=(EnforcementPoint(kind="api_boundary", locator="api.py"),),
                    acceptance_scenarios=(evidence,),
                    disposition=Disposition.PASS,
                )
            )


def test_not_applicable_requires_reason_and_matching_disposition():
    with pytest.raises(ValidationError, match="NOT_APPLICABLE"):
        CompilerObligationRecord(
            **base_record(
                applicability=Applicability.NOT_APPLICABLE,
                disposition=Disposition.NOT_APPLICABLE,
            )
        )
    record = CompilerObligationRecord(
        **base_record(
            applicability=Applicability.NOT_APPLICABLE,
            applicability_reason="The source contract explicitly excludes this deployment target.",
            disposition=Disposition.NOT_APPLICABLE,
        )
    )
    assert record.disposition is Disposition.NOT_APPLICABLE


def test_source_hash_must_be_sha256():
    with pytest.raises(ValidationError, match="source_graph_hash"):
        CompilerObligationRecord(**base_record(source_graph_hash="not-a-hash"))


def test_contract_rejects_unexpected_fields():
    with pytest.raises(ValidationError, match="extra"):
        CompilerObligationRecord(**base_record(backend_id="fastapi"))
