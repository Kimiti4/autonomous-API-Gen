from tiannara.application.compiler.composition import build_compiler_registry


def test_registry_contains_typed_rust_axum_backend():
    registry = build_compiler_registry()
    declarations = {d.backend_id: d for d in registry.declarations()}
    assert {"fastapi_hexagonal", "go_hexagonal", "rust_axum"} <= declarations.keys()
    assert declarations["rust_axum"].metadata["language"] == "rust"
    assert declarations["rust_axum"].metadata["framework"] == "axum"


def test_rust_profile_is_independent_from_python_and_go():
    registry = build_compiler_registry()
    rust = registry.backend("rust_axum").build_profile("taskflow")
    python = registry.backend("fastapi_hexagonal").build_profile("taskflow")
    go = registry.backend("go_hexagonal").build_profile("taskflow")
    assert rust.language == "rust"
    assert rust.test_command == ["cargo", "test", "--locked"]
    assert rust.required_files != python.required_files
    assert rust.required_files != go.required_files


def test_rust_generation_uses_only_system_model():
    backend = build_compiler_registry().backend("rust_axum")
    from tiannara.domain.models.system_model import (
        SystemModel, RequirementsReference, DataModelSpec, FieldSpec,
        AbstractFieldType,
    )
    model = SystemModel(
        system_name="TaskFlow Rust",
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
    result = backend.generate(model)
    assert "src/domain/models.rs" in result.files
    assert "src/main.rs" in result.files
    assert "fastapi" not in "\n".join(result.files.values()).lower()
    assert "net/http" not in "\n".join(result.files.values()).lower()
