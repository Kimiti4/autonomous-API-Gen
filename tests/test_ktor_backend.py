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
    files_lower={x.lower() for x in result.files}
    assert "build.gradle.kts" in result.files
    # Ktor nests sources under src/main/kotlin/.
    assert any(x.endswith("application.kt") for x in files_lower)
    assert "fastapi" not in source and "axum" not in source and "phoenix" not in source
    assert b.build_profile("taskflow").language=="kotlin"


def test_ktor_build_profile_matches_generated_project():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference

    model = SystemModel(
        system_name="TaskFlow Ktor",
        problem_statement="A task system",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    backend = build_compiler_registry().backend("ktor")
    result = backend.generate(model)
    profile = backend.build_profile("taskflow")

    assert profile.build_command == ["gradle", "build"]
    assert profile.test_command == ["gradle", "test"]
    assert profile.runtime_image == "gradle:8-jdk21"
    assert "src/test/kotlin/ApplicationTest.kt" in profile.required_files
    assert "src/main/kotlin/DomainModels.kt" in profile.required_files
    assert "./gradlew" not in " ".join(profile.build_command + profile.test_command)

    app = result.files["src/main/kotlin/Application.kt"]
    test = result.files["src/test/kotlin/ApplicationTest.kt"]
    build = result.files["build.gradle.kts"]
    assert "embeddedServer(Netty" in app
    assert 'call.respondText("ok")' in app
    assert "EngineMain" not in app
    assert "testApplication" in test
    assert 'client.get("/health")' in test
    assert "assertEquals(HttpStatusCode.OK, response.status)" in test
    assert "ktor-server-test-host-jvm" in build
