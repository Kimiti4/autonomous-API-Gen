"""Cap-C Stage 1 — FastAPI hexagonal compiler backend.

Verifies that a real compiler backend turns a typed SystemModel into a
deployable, production-first FastAPI service: correct file layout, an honest
capability manifest, syntactically valid code, inward dependency direction,
deterministic generation, and end-to-end runnable behaviour (service + API +
auth). Backdrop: the Intelligence Foundation floor (Cap-D) is green and this
backend is additive — it touches none of it.
"""

import importlib
import sys

import pytest

from tiannara.application.compiler import (
    BundleVerifier,
    FastAPIHexagonalBackend,
    write_bundle,
)
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.isr import (
    DataModelSpec as LegacyDataModelSpec,
    IntermediateSoftwareRepresentation,
    IntentSpecification,
    SecuritySpec as LegacySecuritySpec,
    ServiceSpec as LegacyServiceSpec,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    BusinessCapability,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SecurityModel,
    SystemModel,
)
from tiannara.domain.ports import CompilerBackend


BACKEND = FastAPIHexagonalBackend()


def _sample_system_model() -> SystemModel:
    return SystemModel(
        system_name="Inventory Tracker",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        capabilities=[BusinessCapability(id="cap-item", name="Item management")],
        data_models=[
            DataModelSpec(
                id="dm-item",
                name="Item",
                owning_service_id="svc-1",
                fields=[
                    FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(name="name", type=AbstractFieldType.TEXT),
                    FieldSpec(name="quantity", type=AbstractFieldType.INTEGER),
                    FieldSpec(
                        name="status",
                        type=AbstractFieldType.ENUMERATION,
                        enumeration_values=["active", "archived"],
                    ),
                ],
            )
        ],
        security=SecurityModel(authentication=AuthenticationPosture.TOKEN_BASED),
    )


def _compile():
    return BACKEND.generate(_sample_system_model())


@pytest.fixture
def generated(tmp_path):
    result = _compile()
    slug = result.system_name
    write_bundle(result, tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        yield slug, tmp_path, result
    finally:
        for module in list(sys.modules):
            if module == slug or module.startswith(slug + "."):
                del sys.modules[module]
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))


def test_compile_emits_expected_files():
    result = _compile()
    slug = result.system_name
    expected = [
        f"{slug}/main.py",
        f"{slug}/config.py",
        f"{slug}/domain/models.py",
        f"{slug}/domain/repositories.py",
        f"{slug}/application/services.py",
        f"{slug}/infrastructure/memory_repositories.py",
        f"{slug}/api/routes.py",
        f"{slug}/api/schemas.py",
        f"{slug}/api/deps.py",
        f"{slug}/tests/test_api.py",
        "requirements.txt",
        "requirements-dev.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
        "README.md",
    ]
    paths = set(result.file_paths())
    for path in expected:
        assert path in paths, f"missing {path}"


def test_capability_manifest_is_honest():
    result = _compile()
    caps = set(result.capability_manifest.capabilities)
    assert BundleCapability.CONTAINERIZE in caps
    assert BundleCapability.HEALTH_CHECK in caps
    assert BundleCapability.OBSERVABILITY in caps
    # Stage 1 deliberately does not provision infra or run DB migrations;
    # those arrive as separate compiler backends.
    assert BundleCapability.INFRASTRUCTURE_PROVISION not in caps
    assert BundleCapability.DATABASE_MIGRATION not in caps
    assert result.capability_manifest.backend_id == "fastapi_hexagonal"


def test_generated_python_files_compile(generated):
    _slug, tmp, result = generated
    slug = result.system_name
    verifier = BundleVerifier(
        package=slug,
        required_files=[f"{slug}/main.py", f"{slug}/domain/models.py", f"{slug}/api/routes.py"],
    )
    report = verifier.verify(tmp)
    assert report.syntax_errors == []
    assert report.missing_files == []
    assert report.ok is True


def test_dependency_direction_is_inward(generated):
    slug, tmp, _ = generated
    verifier = BundleVerifier(package=slug, required_files=[])
    report = verifier.verify(tmp)
    assert report.dependency_violations == []


def test_verifier_detects_missing_files(generated):
    slug, tmp, _ = generated
    verifier = BundleVerifier(package=slug, required_files=["does/not/exist.py"])
    report = verifier.verify(tmp)
    assert report.ok is False
    assert report.missing_files == ["does/not/exist.py"]


def test_compilation_is_deterministic():
    first = BACKEND.generate(_sample_system_model())
    second = BACKEND.generate(_sample_system_model())
    assert first.files == second.files
    assert first.capability_manifest.model_dump() == second.capability_manifest.model_dump()


def test_backend_conforms_to_compiler_port():
    assert isinstance(BACKEND, CompilerBackend)
    assert BACKEND.name == "fastapi_hexagonal"


def test_compile_through_port_writes_bundle(tmp_path):
    model = _sample_system_model()
    isr = IntermediateSoftwareRepresentation.from_system_model("sys-1", model)
    bundle = BACKEND.compile(isr, Genome(genome_id="g1"), str(tmp_path))

    assert isinstance(bundle, SystemDeploymentBundle)
    assert bundle.backend_name == "fastapi_hexagonal"
    assert bundle.project_id == "sys-1"
    assert bundle.isr_hash == isr.content_hash()
    assert bundle.capability_manifest is not None
    slug = BACKEND.generate(model).system_name
    assert (tmp_path / slug / "main.py").exists()


def test_legacy_envelope_synthesizes_system_model(tmp_path):
    isr = IntermediateSoftwareRepresentation(
        system_id="sys-legacy",
        system_name="Legacy Demo",
        intent=IntentSpecification(statement="legacy service", domain="general"),
        services=[LegacyServiceSpec(name="primary")],
        data_models=[
            LegacyDataModelSpec(
                name="widget", fields={"id": "str", "name": "str", "price": "float"}
            )
        ],
        security=LegacySecuritySpec(authentication="anonymous"),
    )
    bundle = BACKEND.compile(isr, Genome(genome_id="g2"), str(tmp_path))

    assert bundle.project_id == "sys-legacy"
    assert bundle.backend_name == "fastapi_hexagonal"
    assert (tmp_path / "legacy_demo" / "main.py").exists()
    assert (tmp_path / "legacy_demo" / "domain" / "models.py").read_text().count(
        "class Widget"
    ) == 1


def test_technology_tokens_rejected_at_envelope():
    from tiannara.domain.models.system_model import (
        TechnologyCouplingError,
    )

    bad = _sample_system_model()
    bad.system_name = "fastapi service"
    with pytest.raises(TechnologyCouplingError):
        IntermediateSoftwareRepresentation.from_system_model("sys-bad", bad)


def test_generated_service_crud(generated):
    slug, _tmp, _ = generated
    services = importlib.import_module(f"{slug}.application.services")
    repositories = importlib.import_module(
        f"{slug}.infrastructure.memory_repositories"
    )

    service = services.ItemService(repositories.InMemoryItemRepository())
    item = service.create(name="Widget", quantity=3, status="active")
    assert item.id
    assert item.name == "Widget"
    assert service.get(item.id).quantity == 3
    assert len(service.list()) == 1
    assert service.delete(item.id) is True
    assert service.get(item.id) is None


def test_generated_api_behaviour(generated):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    from fastapi.testclient import TestClient

    slug, _tmp, _ = generated
    main = importlib.import_module(f"{slug}.main")
    config = importlib.import_module(f"{slug}.config")

    app = main.create_app(config.Settings(api_key="secret"))
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/readiness").status_code == 200
    # Auth-gated resources require a key.
    assert client.get("/items").status_code == 401
    headers = {"X-API-Key": "secret"}
    created = client.post(
        "/items",
        json={"name": "Widget", "quantity": 3, "status": "active"},
        headers=headers,
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert client.get(f"/items/{item_id}", headers=headers).status_code == 200
    assert client.get("/items", headers=headers).status_code == 200
    assert client.delete(f"/items/{item_id}", headers=headers).status_code == 204
    assert client.get(f"/items/{item_id}", headers=headers).status_code == 404


def test_generated_bundle_runs_smoke(tmp_path):
    """The emitted Dockerfile/CI reference the real package entry point."""
    result = _compile()
    compose = result.files["docker-compose.yml"]
    assert "api:" in compose
    ci = result.files[".github/workflows/ci.yml"]
    slug = result.system_name
    assert f"pytest {slug}/tests -q" in ci
