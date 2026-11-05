"""FS-00 route-convergence checks for canonical CompilerIR adoption."""
from __future__ import annotations

import inspect


def test_legacy_lowering_entrypoint_is_a_compiler_ir_adapter():
    from compiler.core.lowering import isr_to_plan, isr_revision_to_compiler_ir

    source = inspect.getsource(isr_to_plan)
    assert "isr_revision_to_compiler_ir(" in source
    assert callable(isr_revision_to_compiler_ir)


def test_campaign_plan_builder_constructs_compiler_ir_before_plan_projection():
    from pathlib import Path

    source = Path("certification/campaign/plan_builder.py").read_text(encoding="utf-8")
    assert "isr_revision_to_compiler_ir(" in source
    assert "compiler_ir.execution_plan" in source
    assert "source_architecture_candidate_content_hash=gh" in source


def test_authorization_campaign_uses_compiler_ir_and_explicit_backend_gate():
    from pathlib import Path

    source = Path("certification/authorization/campaign.py").read_text(encoding="utf-8")
    assert "isr_revision_to_compiler_ir(" in source
    assert "assert_compiler_ir_supported(" in source
    assert "compiler_ir.execution_plan" in source


def test_backend_adapter_is_downstream_of_canonical_ir_boundary():
    from pathlib import Path

    source = Path("compiler/core/canonical_ir.py").read_text(encoding="utf-8")
    assert "class CompilerIRProjectionReport" in source
    assert "assert_compiler_ir_supported" in source
    assert "lost_node_ids" in source
    assert "lost_relationship_ids" in source
