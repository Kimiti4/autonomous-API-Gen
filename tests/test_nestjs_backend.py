from tiannara.application.compiler.composition import build_compiler_registry


def test_registry_contains_nestjs_backend():
    registry = build_compiler_registry()
    declarations = {d.backend_id: d for d in registry.declarations()}
    assert {"fastapi_hexagonal", "go_hexagonal", "rust_axum", "nestjs"} <= declarations.keys()
    assert declarations["nestjs"].metadata["language"] == "typescript"
    assert declarations["nestjs"].metadata["framework"] == "nestjs"


def test_nestjs_profile_is_independent():
    registry = build_compiler_registry()
    profile = registry.backend("nestjs").build_profile("taskflow")
    rust = registry.backend("rust_axum").build_profile("taskflow")
    assert profile.language == "typescript"
    assert profile.build_command == ["npm", "run", "build"]
    assert profile.test_command == ["npm", "test", "--", "--runInBand"]
    assert profile.required_files != rust.required_files


def test_nestjs_generation_consumes_only_system_model():
    from tiannara.domain.models.system_model import (
        SystemModel, RequirementsReference, DataModelSpec, FieldSpec, AbstractFieldType,
    )
    model = SystemModel(
        system_name="TaskFlow Nest",
        problem_statement="A task system",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        data_models=[DataModelSpec(
            id="task", name="Task", owning_service_id="primary",
            fields=[
                FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                FieldSpec(name="title", type=AbstractFieldType.TEXT),
            ],
        )],
    )
    result = build_compiler_registry().backend("nestjs").generate(model)
    source = "\n".join(result.files.values()).lower()
    assert "src/main.ts" in result.files
    assert "fastapi" not in source
    assert "axum" not in source
    assert "net/http" not in source
