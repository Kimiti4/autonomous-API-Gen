"""Typed PHP/Laravel compiler backend.

Emits a minimal bootable Laravel 11 HTTP application. Generated model classes
remain structural shells; business semantics are not implied.
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
from tiannara.domain.models.system_model import AbstractFieldType, SystemModel
from .naming import pascal_case, slugify


_TYPES = {
    AbstractFieldType.IDENTIFIER: "string", AbstractFieldType.TEXT: "string",
    AbstractFieldType.INTEGER: "int", AbstractFieldType.DECIMAL: "float",
    AbstractFieldType.BOOLEAN: "bool", AbstractFieldType.TIMESTAMP: "string",
    AbstractFieldType.ENUMERATION: "string", AbstractFieldType.REFERENCE: "string",
    AbstractFieldType.BINARY: "string", AbstractFieldType.DOCUMENT: "array",
}


class LaravelBackend:
    backend_id = "laravel"

    @property
    def name(self):
        return self.backend_id

    def build_profile(self, system_name):
        return BackendBuildProfile(
            language="php",
            required_files=("composer.json", "artisan", "bootstrap/app.php",
                            "bootstrap/providers.php", "public/index.php",
                            "routes/api.php", "phpunit.xml", "tests/TestCase.php",
                            "tests/Feature/HealthTest.php"),
            verifier_kind="laravel",
            build_command=["composer", "install", "--no-interaction", "--prefer-dist"],
            test_command=["php", "artisan", "test"],
            runtime_image="php:8.3-cli",
            requires_build_phase=True,
        )

    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities),
            quality_profile=0.80,
            metadata={"language": "php", "framework": "laravel", "style": "convention-oriented"},
        )

    def _model(self, isr):
        model = isr.system_model()
        if model is None:
            raise ValueError("LaravelBackend requires a typed SystemModel ISR payload")
        return model

    def compile(self, isr, genome, output_dir):
        result = self.generate(self._model(isr))
        write_bundle(result, output_dir)
        return SystemDeploymentBundle(
            project_id=isr.system_id, backend_name=self.name, isr_hash=isr.content_hash(),
            path=Path(output_dir), artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest,
        )

    def generate(self, model: SystemModel):
        return CompilationResult(
            backend_id=self.backend_id, system_name=slugify(model.system_name),
            files={
                "composer.json": self._composer(),
                "artisan": self._artisan(),
                "bootstrap/app.php": self._bootstrap_app(),
                "bootstrap/providers.php": "<?php\n\nreturn [];\n",
                "bootstrap/cache/.gitignore": "*\n!.gitignore\n",
                "storage/framework/cache/data/.gitignore": "*\n!.gitignore\n",
                "storage/framework/sessions/.gitignore": "*\n!.gitignore\n",
                "storage/framework/views/.gitignore": "*\n!.gitignore\n",
                "storage/logs/.gitignore": "*\n!.gitignore\n",
                "config/app.php": self._app_config(),
                "config/logging.php": self._logging_config(),
                "public/index.php": self._public_index(),
                "routes/api.php": self._routes(),
                "app/Models/GeneratedModels.php": self._models(model),
                "phpunit.xml": self._phpunit(),
                "tests/TestCase.php": self._test_case(),
                "tests/Feature/HealthTest.php": self._test(),
                "Dockerfile": self._docker(),
                "README.md": self._readme(model.system_name),
            },
            capability_manifest=self._manifest(),
        )

    def _composer(self):
        return r'''{
  "name": "esap/generated-laravel",
  "type": "project",
  "require": {"php": "^8.3", "laravel/framework": "^11.0"},
  "require-dev": {"phpunit/phpunit": "^11.0"},
  "autoload": {"psr-4": {"App\\": "app/"}},
  "autoload-dev": {"psr-4": {"Tests\\": "tests/"}},
  "scripts": {
    "post-autoload-dump": ["@php artisan package:discover --ansi"],
    "test": ["@php artisan test"]
  },
  "config": {"optimize-autoloader": true, "preferred-install": "dist"},
  "minimum-stability": "stable",
  "prefer-stable": true
}'''

    def _artisan(self):
        return r'''#!/usr/bin/env php
<?php
use Illuminate\Foundation\Application;
use Symfony\Component\Console\Input\ArgvInput;
define('LARAVEL_START', microtime(true));
require __DIR__.'/vendor/autoload.php';
$app = require_once __DIR__.'/bootstrap/app.php';
$status = $app->handleCommand(new ArgvInput);
exit($status);
'''

    def _bootstrap_app(self):
        return r'''<?php
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(api: __DIR__.'/../routes/api.php', health: '/up')
    ->withMiddleware(function (Middleware $middleware): void {})
    ->withExceptions(function (Exceptions $exceptions): void {})
    ->create();
'''

    def _app_config(self):
        return r'''<?php
return [
    'name' => env('APP_NAME', 'Laravel'),
    'env' => env('APP_ENV', 'production'),
    'debug' => (bool) env('APP_DEBUG', false),
    'url' => env('APP_URL', 'http://localhost'),
    'timezone' => 'UTC',
    'locale' => env('APP_LOCALE', 'en'),
    'fallback_locale' => env('APP_FALLBACK_LOCALE', 'en'),
    'faker_locale' => env('APP_FAKER_LOCALE', 'en_US'),
    'cipher' => 'AES-256-CBC',
    'key' => env('APP_KEY'),
    'previous_keys' => array_filter(explode(',', env('APP_PREVIOUS_KEYS', ''))),
    'maintenance' => ['driver' => 'file', 'store' => 'database'],
];
'''

    def _logging_config(self):
        return r'''<?php
return [
    'default' => env('LOG_CHANNEL', 'stack'),
    'deprecations' => ['channel' => env('LOG_DEPRECATIONS_CHANNEL', 'null'), 'trace' => false],
    'channels' => [
        'stack' => ['driver' => 'stack', 'channels' => ['single'], 'ignore_exceptions' => false],
        'single' => [
            'driver' => 'single',
            'path' => storage_path('logs/laravel.log'),
            'level' => env('LOG_LEVEL', 'debug'),
            'replace_placeholders' => true,
        ],
        'null' => ['driver' => 'monolog', 'handler' => Monolog\\Handler\\NullHandler::class],
    ],
];
'''

    def _public_index(self):
        return r'''<?php
use Illuminate\Foundation\Application;
use Illuminate\Http\Request;
define('LARAVEL_START', microtime(true));
require __DIR__.'/../vendor/autoload.php';
$app = require_once __DIR__.'/../bootstrap/app.php';
$app->handleRequest(Request::capture());
'''

    def _routes(self):
        return r'''<?php
use Illuminate\Support\Facades\Route;
Route::get('/health', static fn () => response()->json(['status' => 'ok']));
'''

    def _phpunit(self):
        return '''<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
 bootstrap="vendor/autoload.php" colors="true">
 <testsuites><testsuite name="Feature"><directory>tests/Feature</directory></testsuite></testsuites>
 <php>
  <env name="APP_ENV" value="testing"/>
  <env name="APP_KEY" value="base64:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="/>
  <env name="CACHE_STORE" value="array"/>
  <env name="SESSION_DRIVER" value="array"/>
  <env name="QUEUE_CONNECTION" value="sync"/>
  <env name="MAIL_MAILER" value="array"/>
 </php>
</phpunit>
'''

    def _test_case(self):
        return r'''<?php
namespace Tests;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
abstract class TestCase extends BaseTestCase {}
'''

    def _models(self, model):
        lines = ["<?php", "namespace App\\Models;", ""]
        for dm in model.data_models:
            lines.extend([
                f"class {pascal_case(dm.name)} extends \\Illuminate\\Database\\Eloquent\\Model {{",
                "    protected $guarded = [];",
                "}", "",
            ])
        return "\n".join(lines)

    def _test(self):
        return r'''<?php
namespace Tests\Feature;
use Tests\TestCase;
class HealthTest extends TestCase
{
    public function test_health_route_returns_ok_json(): void
    {
        $this->getJson('/api/health')->assertOk()->assertExactJson(['status' => 'ok']);
    }
    public function test_framework_health_route_returns_ok(): void
    {
        $this->get('/up')->assertOk();
    }
}
'''

    def _docker(self):
        return r'''FROM php:8.3-cli
WORKDIR /app
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
COPY . .
RUN apt-get update \
    && apt-get install -y --no-install-recommends libonig-dev \
    && docker-php-ext-install mbstring \
    && rm -rf /var/lib/apt/lists/*
RUN composer install --no-interaction --prefer-dist --optimize-autoloader
EXPOSE 8000
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]
'''

    def _readme(self, system_name):
        return f"""# {system_name}

Generated Laravel 11 HTTP application.

Install dependencies with composer install, run tests with php artisan test,
and start the development server with php artisan serve.

The emitted HTTP contract is limited to /up and /api/health. Generated model
classes are structural shells. CRUD, persistence, authentication, and business
operations are not implemented or certified.
"""

    def _manifest(self):
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.BUILD, BundleCapability.TEST,
                BundleCapability.CONTAINERIZE, BundleCapability.HEALTH_CHECK,
                BundleCapability.DOCUMENTATION,
            ],
            metadata={
                "language": "php", "framework": "laravel",
                "style": "convention-oriented",
                "scope": "bootable health-route application; model shells only",
            },
        )
