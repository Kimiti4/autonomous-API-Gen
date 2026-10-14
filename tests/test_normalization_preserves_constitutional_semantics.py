from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.normalization_pass import NormalizationPass
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System


def test_normalization_preserves_non_module_constitutional_semantics():
    semantic_fields = (
        "constraints",
        "business_capabilities",
        "reliability_requirements",
        "architectural_boundaries",
        "requirements",
        "acceptance_criteria",
        "deployment_intents",
        "testing_anchors",
        "documentation_intents",
        "evolution_objectives",
        "protected_regions",
        "evolution_policies",
        "architectural_decisions",
        "security_threats",
    )
    original_values = {name: (object(),) for name in semantic_fields}
    original_system = System(
        id="semantic-preservation",
        name="Semantic preservation",
        **original_values,
    )
    ctx = CompilerContext(
        _isr=ISR(system=original_system),
        _config=CompilationConfig(project_name="semantic-preservation"),
    )

    result = NormalizationPass().execute(ctx)

    assert result.success
    for field_name, original_value in original_values.items():
        assert getattr(ctx.isr.system, field_name) is original_value
