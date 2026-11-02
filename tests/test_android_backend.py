from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import (
    AbstractFieldType, DataModelSpec, FieldSpec, RequirementsReference, SystemModel,
)


def model(**overrides):
    values = dict(
        system_name="Sample Catalogue",
        problem_statement="A static catalogue shell",
        requirements_ref=RequirementsReference(graph_id="fixture", graph_hash="fixture-sha256"),
        data_models=[DataModelSpec(
            id="item", name="Grocery Item", owning_service_id="catalogue",
            fields=[FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(name="label", type=AbstractFieldType.TEXT)],
        )],
    )
    values.update(overrides)
    return SystemModel(**values)


def test_android_backend_is_registered_and_declares_only_supported_capabilities():
    registry = build_compiler_registry()
    backend = registry.backend("android")
    declaration = registry.declaration("android")
    assert backend.backend_id == "android"
    assert declaration.metadata["scope"] == "static-model-shell"
    assert {item.value for item in declaration.capabilities} == {"build", "documentation"}


def test_android_generation_emits_real_android_application_structure():
    result = build_compiler_registry().backend("android").generate(model())
    assert result.files["app/src/main/AndroidManifest.xml"].find("MAIN") >= 0
    source = result.files["app/src/main/java/generated/app/MainActivity.kt"]
    assert "ComponentActivity" in source
    assert "GroceryItem" in source
    assert "Static shell only" in source
    assert "app/build.gradle.kts" in result.files
    assert result.capability_manifest.backend_id == "android"


def test_android_generation_is_deterministic():
    backend = build_compiler_registry().backend("android")
    assert backend.generate(model()).files == backend.generate(model()).files


def test_android_refuses_api_and_service_semantics_instead_of_dropping_them():
    service_model = model(services=[{
        "id": "catalogue", "name": "Catalogue", "domain_id": "domain",
        "responsibilities": ["manage catalogue"],
    }])
    try:
        build_compiler_registry().backend("android").generate(service_model)
    except ValueError as exc:
        assert "refuses service, API, and event semantics" in str(exc)
    else:
        raise AssertionError("unsupported runtime semantics were silently accepted")
