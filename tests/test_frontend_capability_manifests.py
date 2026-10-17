from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


def test_frontend_manifests_do_not_claim_unimplemented_tooling():
    registry = build_compiler_registry()
    model = SystemModel(
        system_name="Capability manifest audit",
        problem_statement="Audit declared compiler operations",
        requirements_ref=RequirementsReference(graph_id="audit", graph_hash="audit"),
    )
    unsupported_claims = {
        BundleCapability.LINT,
        BundleCapability.STATIC_ANALYSIS,
        BundleCapability.SECURITY_SCAN,
        BundleCapability.RELEASE,
    }
    expected = {
        BundleCapability.BUILD,
        BundleCapability.TEST,
        BundleCapability.DOCUMENTATION,
    }
    for backend_id in ("react_ts", "vue_ts", "angular_ts", "next_ts", "nuxt_ts", "svelte_ts"):
        manifest = registry.backend(backend_id).generate(model).capability_manifest
        assert expected <= set(manifest.capabilities), backend_id
        assert not (unsupported_claims & set(manifest.capabilities)), backend_id
