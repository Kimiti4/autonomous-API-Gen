"""Cap-C Stage 2 — CompilerRegistry: opaque storage of backends + declarations."""

import pytest

from tiannara.application.compiler.registry import CompilerRegistry, RegistryError
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability


class _DummyBackend:
    """Opaque backend stand-in — the registry never inspects it."""


def _decl(backend_id="fastapi_hexagonal", quality=0.8):
    return BackendCapabilityDeclaration(
        backend_id=backend_id,
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=[BundleCapability.TEST, BundleCapability.HEALTH_CHECK],
        quality_profile=quality,
    )


def test_register_stores_backend_opaquely_and_returns_declaration():
    reg = CompilerRegistry()
    backend = _DummyBackend()
    declaration = reg.register(backend, _decl())
    assert declaration.backend_id == "fastapi_hexagonal"
    assert reg.backend("fastapi_hexagonal") is backend


def test_duplicate_registration_raises():
    reg = CompilerRegistry()
    reg.register(_DummyBackend(), _decl())
    with pytest.raises(RegistryError):
        reg.register(_DummyBackend(), _decl())


def test_declarations_are_sorted_by_backend_id():
    reg = CompilerRegistry()
    reg.register(_DummyBackend(), _decl("zbackend"))
    reg.register(_DummyBackend(), _decl("abackend"))
    assert [d.backend_id for d in reg.declarations()] == ["abackend", "zbackend"]


def test_lookup_unknown_backend_raises():
    reg = CompilerRegistry()
    with pytest.raises(RegistryError):
        reg.backend("nope")
    with pytest.raises(RegistryError):
        reg.declaration("nope")


def test_contains_and_len_reflect_registration():
    reg = CompilerRegistry()
    assert "fastapi_hexagonal" not in reg
    assert len(reg) == 0
    reg.register(_DummyBackend(), _decl())
    assert "fastapi_hexagonal" in reg
    assert len(reg) == 1


def test_registry_never_exposes_compile():
    # Selection-only seam: no compile()/generate() surface, ever.
    reg = CompilerRegistry()
    assert not hasattr(reg, "compile")
    assert not hasattr(reg, "generate")
