from tiannara.application.compiler.composition import build_compiler_registry


def test_default_registry_contains_independent_python_and_go_backends():
    registry = build_compiler_registry()
    declarations = {d.backend_id: d for d in registry.declarations()}

    assert {"fastapi_hexagonal", "go_hexagonal"} <= declarations.keys()
    assert declarations["fastapi_hexagonal"].metadata["language"] == "python"
    assert declarations["go_hexagonal"].metadata["language"] == "go"
    assert declarations["go_hexagonal"].metadata["framework"] == "net/http"


def test_cross_language_backends_have_distinct_build_profiles():
    registry = build_compiler_registry()

    python_profile = registry.backend("fastapi_hexagonal").build_profile("taskflow")
    go_profile = registry.backend("go_hexagonal").build_profile("taskflow")

    assert python_profile.language == "python"
    assert go_profile.language == "go"
    assert python_profile.required_files != go_profile.required_files
    assert go_profile.test_command == ["go", "test", "./..."]
