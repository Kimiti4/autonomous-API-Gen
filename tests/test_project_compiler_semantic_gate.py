import pytest

from tiannara.application.compiler.project_compiler import ProjectCompiler
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.domain.models.semantic_resolution import UnresolvedSemanticsError


def test_taskflow_mode_activates_gate_before_backend_planning():
    class GateIntentCompiler:
        def compile_full(self, statement, system_id, *, taskflow_semantic_gate=False):
            assert taskflow_semantic_gate is True
            raise UnresolvedSemanticsError(
                ("authorization.workspace_membership_scope",)
            )

    compiler = ProjectCompiler(
        GateIntentCompiler(),
        CompilerRegistry(),
        taskflow_semantic_gate=True,
    )

    with pytest.raises(UnresolvedSemanticsError, match="workspace_membership_scope"):
        compiler.compile_intent("Build TaskFlow", {})
