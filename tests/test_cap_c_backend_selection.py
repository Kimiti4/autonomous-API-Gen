"""Cap-C Stage 2 — capability-driven backend selection."""

import pytest

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.application.compiler.selector import (
    BackendSelectionError,
    BackendSelector,
    SelectionPolicy,
    plan_compilation,
)
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
    CompilationRequirement,
)
from tiannara.domain.models.capability_manifest import BundleCapability


def _declaration(backend_id="fastapi_hexagonal", quality=0.8, caps=None):
    base = [
        BundleCapability.TEST,
        BundleCapability.HEALTH_CHECK,
        BundleCapability.CONTAINERIZE,
    ]
    return BackendCapabilityDeclaration(
        backend_id=backend_id,
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=caps if caps is not None else base,
        quality_profile=quality,
    )


def _requirement():
    return CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
            BundleCapability.CONTAINERIZE,
        ],
    )


def _registry_with_real_fastapi_and_dummy():
    reg = CompilerRegistry()
    # The REAL backend is registered opaquely; selection never invokes it.
    reg.register(FastAPIHexagonalBackend(), _declaration("fastapi_hexagonal", 0.8))
    reg.register(_Dummy(), _declaration("dummy_higher", 0.9))
    reg.register(
        _Dummy(), _declaration("dummy_missing", 0.7, caps=[BundleCapability.TEST])
    )
    return reg


class _Dummy:
    pass


def test_select_picks_highest_quality_satisfying_backend():
    reg = _registry_with_real_fastapi_and_dummy()
    chosen = BackendSelector(reg).select(_requirement())
    assert chosen.backend_id == "dummy_higher"


def test_rank_is_deterministic_ordering():
    reg = _registry_with_real_fastapi_and_dummy()
    ranked = BackendSelector(reg).rank(_requirement())
    assert [d.backend_id for d in ranked] == ["dummy_higher", "fastapi_hexagonal"]


def test_selection_error_when_nothing_satisfies():
    reg = CompilerRegistry()
    reg.register(_Dummy(), _declaration("only_test", 0.9, caps=[BundleCapability.TEST]))
    with pytest.raises(BackendSelectionError):
        BackendSelector(reg).select(_requirement())


def test_policy_filters_low_quality_backends():
    reg = CompilerRegistry()
    reg.register(_Dummy(), _declaration("weak", quality=0.4))
    reg.register(_Dummy(), _declaration("strong", quality=0.9))
    chosen = BackendSelector(reg).select(
        _requirement(), policy=SelectionPolicy(min_quality_profile=0.8)
    )
    assert chosen.backend_id == "strong"


def test_plan_compilation_emits_one_plan_per_requirement():
    reg = _registry_with_real_fastapi_and_dummy()
    requirements = [_requirement(), _requirement()]
    plan = plan_compilation(reg, requirements)
    assert len(plan.planned) == 2
    # Deterministic identifier survives a rebuild.
    assert plan.plan_id == plan_compilation(reg, requirements).plan_id


def test_plan_compilation_raises_when_unsatisfiable():
    reg = CompilerRegistry()
    reg.register(_Dummy(), _declaration("only_test", 0.9, caps=[BundleCapability.TEST]))
    with pytest.raises(BackendSelectionError):
        plan_compilation(reg, [_requirement()])


def test_selected_backend_referred_to_by_id_only():
    # The plan references the real backend by id without invoking it.
    reg = CompilerRegistry()
    backend = FastAPIHexagonalBackend()
    reg.register(backend, _declaration("fastapi_hexagonal", 0.8))
    plan = plan_compilation(reg, [_requirement()])
    chosen = plan.planned[0]
    assert chosen.backend_id == "fastapi_hexagonal"
    assert isinstance(reg.backend(chosen.backend_id), FastAPIHexagonalBackend)
