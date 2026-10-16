from tiannara.application.compiler.composition import build_compiler_registry

def test_express_backend_is_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert "express" in ids
    d=next(x for x in build_compiler_registry().declarations() if x.backend_id=="express")
    assert d.metadata["runtime"]=="node.js"

def test_express_is_distinct_from_nestjs():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Express Test",problem_statement="test",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    b=build_compiler_registry().backend("express")
    result=b.generate(model)
    assert "src/index.ts" in result.files
    assert '"skipLibCheck":true' in result.files["tsconfig.json"]
    assert "@nestjs" not in "\n".join(result.files.values())


def test_express_generated_health_test_exercises_live_http_endpoint():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    from tiannara.domain.models.capability_manifest import BundleCapability

    model = SystemModel(
        system_name="Express Health Contract",
        problem_statement="Exercise the generated health endpoint",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    backend = build_compiler_registry().backend("express")
    generated = backend.generate(model)
    test_source = generated.files["test/app.test.ts"]
    assert "expect(true).toBe(true)" not in test_source
    assert 'createApp().listen(0, "127.0.0.1")' in test_source
    assert 'fetch(baseUrl + "/health")' in test_source
    assert "expect(response.status).toBe(200)" in test_source
    assert 'expect(await response.json()).toEqual({ status: "ok" })' in test_source
    assert 'fetch(baseUrl + "/not-a-route")' in test_source
    assert backend.build_profile(model.system_name).test_command == ["npm", "test"]
    unsupported = {
        BundleCapability.LINT, BundleCapability.STATIC_ANALYSIS,
        BundleCapability.SECURITY_SCAN, BundleCapability.DEPLOY,
        BundleCapability.OBSERVABILITY, BundleCapability.RELEASE,
    }
    assert not (unsupported & set(generated.capability_manifest.capabilities))


def test_express_runtime_entrypoint_matches_typescript_output_layout():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference

    model = SystemModel(
        system_name="Express Runtime Entrypoint",
        problem_statement="Verify the compiled entrypoint used by local and container execution",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    generated = build_compiler_registry().backend("express").generate(model)
    package = generated.files["package.json"]
    dockerfile = generated.files["Dockerfile"]
    tsconfig = generated.files["tsconfig.json"]

    # TypeScript preserves the src/ directory under outDir=dist.
    assert '"outDir":"dist"' in tsconfig
    assert '"start":"node dist/src/index.js"' in package
    assert 'CMD ["node","dist/src/index.js"]' in dockerfile
    assert 'dist/index.js' not in package
    assert 'dist/index.js' not in dockerfile
