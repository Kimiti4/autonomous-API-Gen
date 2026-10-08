from tiannara.application.compiler.composition import build_compiler_registry

def test_registry_contains_ktor():
    registry=build_compiler_registry()
    ids={d.backend_id for d in registry.declarations()}
    assert {"fastapi_hexagonal","go_hexagonal","rust_axum","nestjs","spring_boot","aspnet_core","phoenix","ktor"} <= ids

def test_ktor_is_independent():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference, DataModelSpec, FieldSpec, AbstractFieldType
    model=SystemModel(system_name="TaskFlow Ktor",problem_statement="A task system",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"),
      data_models=[DataModelSpec(id="task",name="Task",owning_service_id="primary",
        fields=[FieldSpec(name="id",type=AbstractFieldType.IDENTIFIER),
                FieldSpec(name="title",type=AbstractFieldType.TEXT)])])
    b=build_compiler_registry().backend("ktor")
    result=b.generate(model)
    source="\n".join(result.files.values()).lower()
    assert "build.gradle.kts" in result.files
    assert "application.kt" in {x.lower() for x in result.files}
    assert "fastapi" not in source and "axum" not in source and "phoenix" not in source
    assert b.build_profile("taskflow").language=="kotlin"
