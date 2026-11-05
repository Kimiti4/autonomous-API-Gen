"""Typed Ruby/Rails compiler backend.

Emits a minimal bootable Rails 8 HTTP application. Generated model classes
remain structural shells; business semantics and persistence are not implied.
"""
from __future__ import annotations

from pathlib import Path

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.backend_declaration import ArtifactKind, BackendCapabilityDeclaration
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.system_model import SystemModel
from .naming import pascal_case, slugify


class RailsBackend:
    backend_id = "rails"

    @property
    def name(self):
        return self.backend_id

    def build_profile(self, system_name):
        return BackendBuildProfile(
            language="ruby",
            required_files=(
                "Gemfile",
                "Rakefile",
                "config.ru",
                "config/boot.rb",
                "config/application.rb",
                "config/environment.rb",
                "config/database.yml",
                "config/routes.rb",
                "app/controllers/application_controller.rb",
                "app/controllers/health_controller.rb",
                "app/models/application_record.rb",
                "app/models/generated_models.rb",
                "test/test_helper.rb",
                "test/controllers/health_controller_test.rb",
                "bin/rails",
            ),
            verifier_kind="rails",
            build_command=["bundle", "install"],
            test_command=["bundle", "exec", "rails", "test"],
            runtime_image="ruby:3.3",
            requires_build_phase=True,
        )

    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities),
            quality_profile=0.80,
            metadata={
                "language": "ruby",
                "framework": "rails",
                "style": "convention-over-configuration",
            },
        )

    def _model(self, isr):
        model = isr.system_model()
        if model is None:
            raise ValueError("RailsBackend requires a typed SystemModel ISR payload")
        return model

    def compile(self, isr, genome, output_dir):
        result = self.generate(self._model(isr))
        write_bundle(result, output_dir)
        return SystemDeploymentBundle(
            project_id=isr.system_id,
            backend_name=self.name,
            isr_hash=isr.content_hash(),
            path=Path(output_dir),
            artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest,
        )

    def generate(self, model: SystemModel):
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slugify(model.system_name),
            files={
                "Gemfile": self._gemfile(),
                "Rakefile": self._rakefile(),
                "config.ru": self._config_ru(),
                "config/boot.rb": self._boot(),
                "config/application.rb": self._application(),
                "config/environment.rb": self._environment(),
                "config/database.yml": self._database(),
                "config/routes.rb": self._routes(),
                "app/controllers/application_controller.rb": self._base_controller(),
                "app/controllers/health_controller.rb": self._health_controller(),
                "app/models/application_record.rb": self._application_record(),
                "app/models/generated_models.rb": self._models(model),
                "test/test_helper.rb": self._test_helper(),
                "test/controllers/health_controller_test.rb": self._test(),
                "bin/rails": self._bin_rails(),
                "Dockerfile": self._docker(),
                "README.md": self._readme(model.system_name),
            },
            capability_manifest=self._manifest(),
        )

    def _gemfile(self):
        return '''source "https://rubygems.org"

gem "rails", "~> 8.0"
gem "puma", "~> 6.0"
gem "sqlite3", "~> 2.1"
'''

    def _rakefile(self):
        return '''require_relative "config/application"
Rails.application.load_tasks
'''

    def _config_ru(self):
        return '''require_relative "config/environment"
run Rails.application
Rails.application.load_server
'''

    def _boot(self):
        return '''ENV["BUNDLE_GEMFILE"] ||= File.expand_path("../Gemfile", __dir__)
require "bundler/setup"
'''

    def _application(self):
        return '''require_relative "boot"
require "rails/all"
Bundler.require(*Rails.groups)

module GeneratedRails
  class Application < Rails::Application
    config.load_defaults 8.0
    config.eager_load = false
    config.secret_key_base = ENV.fetch(
      "SECRET_KEY_BASE",
      "generated-development-secret-key-base-change-before-production-000000000000"
    )
    config.active_record.dump_schema_after_migration = false
  end
end
'''

    def _environment(self):
        return '''require_relative "application"
Rails.application.initialize!
'''

    def _database(self):
        return '''default: &default
  adapter: sqlite3
  pool: <%= ENV.fetch("RAILS_MAX_THREADS", 5) %>
  timeout: 5000

development:
  <<: *default
  database: storage/development.sqlite3

test:
  <<: *default
  database: storage/test.sqlite3

production:
  <<: *default
  database: storage/production.sqlite3
'''

    def _routes(self):
        return '''Rails.application.routes.draw do
  get "/health", to: "health#show"
end
'''

    def _base_controller(self):
        return '''class ApplicationController < ActionController::API
end
'''

    def _health_controller(self):
        return '''class HealthController < ApplicationController
  def show
    render json: { status: "ok" }
  end
end
'''

    def _application_record(self):
        return '''class ApplicationRecord < ActiveRecord::Base
  primary_abstract_class
end
'''

    def _models(self, model):
        lines = []
        for dm in model.data_models:
            lines.extend([
                f"class {pascal_case(dm.name)} < ApplicationRecord",
                "end",
                "",
            ])
        return "\\n".join(lines)

    def _test_helper(self):
        return '''ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

class ActiveSupport::TestCase
  parallelize(workers: 1)
end
'''

    def _test(self):
        return '''require "test_helper"

class HealthControllerTest < ActionDispatch::IntegrationTest
  test "health endpoint returns the expected JSON contract" do
    get "/health"
    assert_response :success
    assert_equal "ok", response.parsed_body["status"]
  end
end
'''

    def _bin_rails(self):
        return '''#!/usr/bin/env ruby
APP_PATH = File.expand_path("../config/application", __dir__)
require_relative "../config/boot"
require "rails/commands"
'''

    def _docker(self):
        return '''FROM ruby:3.3
WORKDIR /app
RUN apt-get update \\
    && apt-get install -y --no-install-recommends build-essential libsqlite3-dev \\
    && rm -rf /var/lib/apt/lists/*
COPY Gemfile Gemfile.lock* ./
RUN bundle install
COPY . .
EXPOSE 3000
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
'''

    def _readme(self, system_name):
        return f"""# {system_name}

Generated Rails 8 HTTP application.

## Build and test

\`\`\`sh
bundle install
bundle exec rails test
bundle exec rails server -b 0.0.0.0
\`\`\`

The generated HTTP contract is limited to GET /health. Generated model
classes are structural shells; migrations, schema, CRUD, authentication,
authorization, and business operations are not implemented or certified.
"""

    def _manifest(self):
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.CONTAINERIZE,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.DOCUMENTATION,
            ],
            metadata={
                "language": "ruby",
                "framework": "rails",
                "style": "convention-over-configuration",
                "scope": "bootable health-route application; model shells only",
            },
        )
