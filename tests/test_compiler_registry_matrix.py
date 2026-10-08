from tiannara.application.compiler.composition import build_compiler_registry

def test_all_current_backend_targets_are_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert {"fastapi_hexagonal","go_hexagonal","rust_axum","nestjs","spring_boot","aspnet_core","phoenix","ktor"} <= ids

def test_ktor_profile_is_language_specific():
    b=build_compiler_registry().backend("ktor")
    p=b.build_profile("taskflow")
    assert p.language=="kotlin"
    assert p.build_command==["./gradlew","build"]
    assert p.test_command==["./gradlew","test"]
