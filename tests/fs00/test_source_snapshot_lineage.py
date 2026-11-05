from types import SimpleNamespace

import pytest

from app.engine.source_bound_full_stack import source_snapshot_from_plan_artifacts


class Dumpable:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, *args, **kwargs):
        return self.payload


def artifacts():
    plan = {"plan_id": "plan-1", "isr_id": "system-1", "services": []}
    revision = {
        "system_id": "system-1",
        "revision_id": "rev-1",
        "schema_version": "2.0",
        "content_hash": "a" * 64,
        "revision_hash": "b" * 64,
        "graph": {"nodes": {"service:payroll": {"id": "service:payroll"}}},
    }
    compiler_ir = {
        "compilation_id": "compiler-ir-1",
        "content_hash": "c" * 64,
        "execution_plan": plan,
        "source_isr_revision_id": "rev-1",
        "source_isr_schema_version": "2.0",
        "source_isr_content_hash": "a" * 64,
        "source_isr_revision_hash": "b" * 64,
    }
    genome = {
        "genes": [],
        "source_isr_revision_id": "rev-1",
        "source_isr_schema_version": "2.0",
        "source_isr_content_hash": "a" * 64,
        "source_isr_revision_hash": "b" * 64,
    }
    return SimpleNamespace(
        plan=Dumpable(plan),
        revision=Dumpable(revision),
        compiler_ir=Dumpable(compiler_ir),
        genome=Dumpable(genome),
        requirement_graph=Dumpable({"nodes": {"req:payroll": {"id": "req:payroll"}}, "edges": {}}),
        requirement_graph_hash="d" * 64,
        genome_hash="e" * 64,
        plan_hash="f" * 64,
    )


def test_source_snapshot_binds_exact_isr_revision_and_compiler_ir():
    snapshot = source_snapshot_from_plan_artifacts(artifacts())
    assert snapshot["schema"] == "source-bound-plan-snapshot/2"
    assert snapshot["declared_hashes"]["isr_content_hash"] == "a" * 64
    assert snapshot["declared_hashes"]["isr_revision_hash"] == "b" * 64
    assert snapshot["declared_hashes"]["compiler_ir_id"] == "compiler-ir-1"
    assert snapshot["declared_hashes"]["compiler_ir_hash"] == "c" * 64


def test_source_snapshot_rejects_plan_that_differs_from_compiler_ir():
    item = artifacts()
    item.plan = Dumpable({"plan_id": "stale", "isr_id": "system-1", "services": []})
    with pytest.raises(ValueError, match="does not match canonical CompilerIR"):
        source_snapshot_from_plan_artifacts(item)


def test_source_snapshot_rejects_compiler_ir_bound_to_another_revision():
    item = artifacts()
    item.compiler_ir = Dumpable({
        **item.compiler_ir.payload,
        "source_isr_revision_hash": "9" * 64,
    })
    with pytest.raises(ValueError, match="revision-envelope hash"):
        source_snapshot_from_plan_artifacts(item)
