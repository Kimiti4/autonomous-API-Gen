from __future__ import annotations

import json

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


def _model() -> SystemModel:
    return SystemModel(
        system_name="Laravel Contract",
        problem_statement="A minimal generated Laravel application",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )


def test_laravel_profile_requires_a_real_bootstrap_and_http_test():
    backend = build_compiler_registry().backend("laravel")
    profile = backend.build_profile("Laravel Contract")

    assert profile.language == "php"
    assert profile.build_command[:2] == ["composer", "install"]
    assert profile.test_command == ["php", "artisan", "test"]
    assert {
        "bootstrap/app.php",
        "bootstrap/providers.php",
        "public/index.php",
        "routes/api.php",
        "phpunit.xml",
        "tests/TestCase.php",
        "tests/Feature/HealthTest.php",
    } <= set(profile.required_files)


def test_laravel_generation_emits_bootable_http_contract_and_real_test():
    backend = build_compiler_registry().backend("laravel")
    result = backend.generate(_model())
    files = result.files

    composer = json.loads(files["composer.json"])
    assert composer["require"]["laravel/framework"] == "^11.0"
    assert composer["require-dev"]["phpunit/phpunit"] == "^11.0"
    assert composer["autoload"]["psr-4"] == {"App\\": "app/"}
    assert composer["autoload-dev"]["psr-4"] == {"Tests\\": "tests/"}

    assert "Application::configure" in files["bootstrap/app.php"]
    assert "routes/api.php" in files["bootstrap/app.php"]
    assert "health: '/up'" in files["bootstrap/app.php"]
    assert "handleRequest(Request::capture())" in files["public/index.php"]
    assert "Route::get('/health'" in files["routes/api.php"]

    health_test = files["tests/Feature/HealthTest.php"]
    assert "getJson('/api/health')" in health_test
    assert "assertOk()" in health_test
    assert "assertExactJson(['status' => 'ok'])" in health_test
    assert "assertTrue(true)" not in health_test
    assert "extends BaseTestCase" in files["tests/TestCase.php"]

    assert "composer install" in files["Dockerfile"]
    assert 'CMD ["php", "artisan", "serve"' in files["Dockerfile"]


def test_laravel_manifest_does_not_claim_unimplemented_delivery_controls():
    backend = build_compiler_registry().backend("laravel")
    capabilities = set(backend._manifest().capabilities)

    assert "BUILD" in {item.value for item in capabilities}
    assert "TEST" in {item.value for item in capabilities}
    assert "HEALTH_CHECK" in {item.value for item in capabilities}
    assert not {"LINT", "STATIC_ANALYSIS", "SECURITY_SCAN", "DEPLOY",
                "OBSERVABILITY", "RELEASE"} & {item.value for item in capabilities}
