from tiannara.application.compiler.composition import build_compiler_registry

def test_registry_contains_aspnet_core():
    registry=build_compiler_registry()
    d={x.backend_id:x for x in registry.declarations()}
    assert {"fastapi_hexagonal","go_hexagonal","rust_axum","nestjs","spring_boot","aspnet_core"} <= d.keys()
    assert d["aspnet_core"].metadata["language"]=="csharp"
    assert d["aspnet_core"].metadata["framework"]=="aspnet-core"

def test_aspnet_generation_is_independent():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference, DataModelSpec, FieldSpec, AbstractFieldType
    model=SystemModel(system_name="TaskFlow DotNet",problem_statement="A task system",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"),
      data_models=[DataModelSpec(id="task",name="Task",owning_service_id="primary",
        fields=[FieldSpec(name="id",type=AbstractFieldType.IDENTIFIER),FieldSpec(name="title",type=AbstractFieldType.TEXT)])])
    backend=build_compiler_registry().backend("aspnet_core")
    result=backend.generate(model)
    source="\n".join(result.files.values()).lower()
    assert "GeneratedApp.csproj" in result.files
    assert "Program.cs" in result.files
    assert 'dotnet build' == " ".join(backend.build_profile("taskflow").build_command)
    assert "fastapi" not in source and "spring" not in source and "nestjs" not in source
