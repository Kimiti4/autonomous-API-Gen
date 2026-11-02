"""W14 authorization boundary: unsupported policies must not be dropped."""
from __future__ import annotations

import pytest

from tiannara.application.compiler.angular_frontend import AngularFrontend
from tiannara.application.compiler.frontend_targets import UnsupportedAuthorizationError
from tiannara.application.compiler.hologram_frontend import HologramFrontend
from tiannara.application.compiler.liveview_frontend import LiveViewFrontend
from tiannara.application.compiler.next_frontend import NextFrontend
from tiannara.application.compiler.nuxt_frontend import NuxtFrontend
from tiannara.application.compiler.react_frontend import ReactFrontend
from tiannara.application.compiler.scenic_frontend import ScenicFrontend
from tiannara.application.compiler.svelte_frontend import SvelteFrontend
from tiannara.application.compiler.vue_frontend import VueFrontend
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.system_model import (
    AuthorizationModel,
    RequirementsReference,
    SecurityModel,
    SystemModel,
)


FRONTENDS = (
    ReactFrontend(),
    VueFrontend(),
    SvelteFrontend(),
    AngularFrontend(),
    NextFrontend(),
    NuxtFrontend(),
    LiveViewFrontend(),
    ScenicFrontend(),
    HologramFrontend(),
)
W14_FRONTENDS = (LiveViewFrontend(), ScenicFrontend(), HologramFrontend())
AUTHORIZATION_MODELS = (
    AuthorizationModel.RBAC,
    AuthorizationModel.ABAC,
    AuthorizationModel.POLICY_BASED,
)


def _model(authorization: AuthorizationModel = AuthorizationModel.NONE) -> SystemModel:
    return SystemModel(
        system_name="Authorization Boundary",
        requirements_ref=RequirementsReference(graph_id="w14", graph_hash="fixture"),
        security=SecurityModel(authorization=authorization),
    )


@pytest.mark.parametrize("compiler", FRONTENDS, ids=lambda compiler: compiler.backend_id)
@pytest.mark.parametrize("authorization", AUTHORIZATION_MODELS, ids=lambda value: value.value)
def test_frontends_fail_closed_on_unimplemented_authorization(compiler, authorization) -> None:
    model = _model(authorization)

    with pytest.raises(
        UnsupportedAuthorizationError,
        match=f"cannot enforce declared {authorization.value}",
    ):
        compiler.generate(model)


@pytest.mark.parametrize("compiler", W14_FRONTENDS, ids=lambda compiler: compiler.backend_id)
def test_w14_frontend_bundle_declares_its_required_files(compiler) -> None:
    result = compiler.generate(_model())
    required = set(compiler.build_profile("Authorization Boundary").required_files)

    assert required <= set(result.files)
    assert not result.capability_manifest.provides(BundleCapability.DEPLOY)


def test_frontend_target_registry_does_not_claim_production_readiness() -> None:
    from tiannara.application.compiler.frontend_targets import FRONTEND_TARGETS

    assert {target.target_id for target in FRONTEND_TARGETS} == {
        compiler.backend_id for compiler in FRONTENDS
    }
    assert all(not target.production_ready for target in FRONTEND_TARGETS)
