from __future__ import annotations

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


def _model() -> SystemModel:
    return SystemModel(
        system_name="Rails Contract",
        problem_statement="A minimal generated Rails application",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )


def test_rails_profile_requires_application_bootstrap_and_behavioral_test():
    backend = build_compiler_registry().backend("rails")
    profile = backend.build_profile("Rails Contract")

    assert profile.language == "ruby"
    assert profile.build_command == ["bundle", "install"]
    assert profile.test_command == ["bundle", "exec", "rails", "test"]
    assert {
        "Gemfile", "Rakefile", "config.ru", "config/boot.rb",
        "config/application.rb", "config/environment.rb", "config/database.yml",
        "config/routes.rb", "app/controllers/application_controller.rb",
        "app/controllers/health_controller.rb", "app/models/application_record.rb",
        "test/test_helper.rb", "test/controllers/health_controller_test.rb",
    } <= set(profile.required_files)


def test_rails_generation_emits_bootable_app_and_real_http_test():
    backend = build_compiler_registry().backend("rails")
    result = backend.generate(_model())
    files = result.files

    assert 'gem "rails", "~> 8.0"' in files["Gemfile"]
    assert 'gem "sqlite3", "~> 2.1"' in files["Gemfile"]
    assert 'require "rails/all"' in files["config/application.rb"]
    assert "config.load_defaults 8.0" in files["config/application.rb"]
    assert "Rails.application.initialize!" in files["config/environment.rb"]
    assert "adapter: sqlite3" in files["config/database.yml"]
    assert 'get "/health", to: "health#show"' in files["config/routes.rb"]
    assert 'render json: { status: "ok" }' in files["app/controllers/health_controller.rb"]

    test = files["test/controllers/health_controller_test.rb"]
    assert 'get "/health"' in test
    assert "assert_response :success" in test
    assert 'response.parsed_body["status"]' in test
    assert "COPY Gemfile ./" in files["Dockerfile"]
    assert 'CMD ["bundle", "exec", "rails", "server"' in files["Dockerfile"]


def test_rails_manifest_does_not_claim_unimplemented_delivery_controls():
    backend = build_compiler_registry().backend("rails")
    values = {item.value for item in backend._manifest().capabilities}

    assert {"build", "test", "health_check", "containerize", "documentation"} <= values
    assert not {
        "lint", "static_analysis", "security_scan", "deploy",
        "observability", "release",
    } & values
