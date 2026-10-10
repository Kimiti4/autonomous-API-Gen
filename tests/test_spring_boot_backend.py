from tiannara.application.compiler.composition import build_compiler_registry

def test_registry_contains_spring_boot():
    registry=build_compiler_registry()
    d={x.backend_id:x for x in registry.declarations()}
    assert {"fastapi_hexagonal","go_hexagonal","rust_axum","nestjs","spring_boot"} <= d.keys()
    assert d["spring_boot"].metadata["language"]=="java"
    assert d["spring_boot"].metadata["framework"]=="spring-boot"

def test_spring_profile_and_generation_are_independent():
    registry=build_compiler_registry()
    p=registry.backend("spring_boot").build_profile("taskflow")
    assert p.language=="java"
    assert p.build_command==["./mvnw","test"]
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference, DataModelSpec, FieldSpec, AbstractFieldType
    model=SystemModel(system_name="TaskFlow Spring",problem_statement="A task system",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"),
      data_models=[DataModelSpec(id="task",name="Task",owning_service_id="primary",
        fields=[FieldSpec(name="id",type=AbstractFieldType.IDENTIFIER),
                FieldSpec(name="title",type=AbstractFieldType.TEXT)])])
    result=registry.backend("spring_boot").generate(model)
    source="\n".join(result.files.values()).lower()
    assert "pom.xml" in result.files
    assert "src/main/java/com/generated/application.java" in {x.lower() for x in result.files}
    assert "fastapi" not in source and "axum" not in source and "nestjs" not in source