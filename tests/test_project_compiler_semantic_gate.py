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


def _taskflow_compilation(*, obligations):
    from types import SimpleNamespace

    from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
    from tiannara.domain.models.semantic_resolution import SemanticResolutionRecord
    from tiannara.domain.models.system_model import RequirementsReference, SystemModel

    model = SystemModel(
        system_name="TaskFlow",
        requirements_ref=RequirementsReference(graph_id="taskflow-test", graph_hash="a" * 64),
    )
    record = SemanticResolutionRecord(
        graph_id="taskflow-test",
        graph_hash="a" * 64,
        required_fields=(),
        resolutions=(),
    )
    return SimpleNamespace(
        isr=IntermediateSoftwareRepresentation.from_system_model("taskflow-test", model),
        call_records=[],
        semantic_resolution_record=record,
        requirement_graph=object(),
        authorization_semantic_obligations=obligations,
    )


@pytest.mark.parametrize(
    ("obligations", "message"),
    [
        (None, "typed authorization obligations are missing"),
        (object(), "no registered backend/runtime consumer currently proves enforcement"),
    ],
)
def test_taskflow_generation_stays_blocked_until_authorization_is_enforced(
    monkeypatch, obligations, message
):
    import tiannara.application.compiler.project_compiler as project_compiler_module

    monkeypatch.setattr(
        project_compiler_module, "require_taskflow_semantics", lambda *_args: None
    )

    class GateIntentCompiler:
        def compile_full(self, statement, system_id, *, taskflow_semantic_gate=False):
            assert taskflow_semantic_gate is True
            return _taskflow_compilation(obligations=obligations)

    compiler = ProjectCompiler(
        GateIntentCompiler(),
        CompilerRegistry(),
        taskflow_semantic_gate=True,
    )

    with pytest.raises(ValueError, match=message):
        compiler.compile_intent("Build TaskFlow", {})
