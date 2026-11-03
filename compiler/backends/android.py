"""Campaign-native Android structural backend.

This backend emits only a static catalogue shell. It consumes CompilationPlan,
rejects unsupported runtime/frontend semantics before emission, and remains
STRUCTURAL until independently reviewed runtime evidence justifies promotion.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from isr.core.revision import ISRRevision
from compiler.core.capabilities import (
    BackendCapabilities, assert_frontend_plan_supported, assert_plan_supported,
)
from compiler.core.conformance import CHECKER, ConformanceReport
from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from compiler.core.protocol import BackendClass, BackendIdentity, TestSpec
from compiler.core.repository import GeneratedRepository, build_repository


@dataclass(frozen=True)
class AndroidCandidate:
    revision_hash: str
    plan_hash: str
    repository: GeneratedRepository


class AndroidStructuralBackend:
    name = "android"
    language = "kotlin"
    framework = "jetpack-compose"
    version = "0.1.0"

    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name=self.name, language=self.language, framework=self.framework,
            version=self.version, backend_class=BackendClass.STRUCTURAL,
        )

    def test_spec(self) -> TestSpec:
        # Native build contract only. CampaignRunner currently skips execution
        # stages for STRUCTURAL backends; its Docker runner is not Android-aware.
        return TestSpec(
            command=["gradle", ":app:assembleDebug", "--no-daemon"],
            runs_in="build", build_target="build",
        )

    def capabilities(self) -> BackendCapabilities:
        # Empty by design: no executable Android semantic feature is certified.
        return BackendCapabilities(
            backend_id=self.name, version=self.version, supported_features=frozenset()
        )

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]:
        paths: dict[str, str] = {}
        catalogue = "app/src/main/java/generated/app/MainActivity.kt"
        for service in plan.services:
            paths[service.id] = catalogue
            for model in service.data_models:
                paths[model.id] = catalogue
            for event in service.published_events + service.consumed_events:
                paths[event.id] = catalogue
        for model in plan.data_models:
            paths[model.id] = catalogue
        for event in plan.events:
            paths[event.id] = catalogue
        for policy in plan.security:
            paths[policy.policy_id] = catalogue
        paths.update({
            "infra:docker": "Dockerfile",
            "infra:k8s": "k8s/deployment.yaml",
            "infra:ci": ".github/workflows/android-structural.yml",
            "infra:readme": "README.md",
            "infra:main": catalogue,
            "infra:repositories": "docs/runtime-boundary.md",
            "infra:docs": "docs/architecture.md",
            "infra:semantic_obligations": "docs/semantic-obligations.json",
        })
        return paths

    @staticmethod
    def _assert_static_shell_only(plan: CompilationPlan) -> None:
        unsupported_collections = {
            "services": plan.services,
            "events": plan.events,
            "security policies": plan.security,
            "API operations": plan.apis,
            "effects": plan.effects,
            "effect bindings": plan.effect_bindings,
            "consequences": plan.consequences,
            "invariants": plan.invariants,
            "frontend routes": plan.frontend_routes,
            "frontend interactions": plan.frontend_interactions,
        }
        present = [name for name, items in unsupported_collections.items() if items]
        if present:
            raise ValueError(
                "Android structural backend refuses plan elements outside the "
                f"static data-model catalogue: {', '.join(present)}"
            )
        if not plan.data_models:
            raise ValueError("Android structural backend requires at least one data model")
        if any(model.behavior is not None for model in plan.data_models):
            raise ValueError("Android structural backend refuses typed data-model behavior")

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_plan_supported(plan, self.capabilities())
        assert_frontend_plan_supported(plan, self.capabilities())
        self._assert_static_shell_only(plan)
        model_names = [model.entity_name for model in plan.data_models]
        quoted = ",\n                ".join(json.dumps(name) for name in model_names)
        title = json.dumps(plan.isr_id)
        source = f'''package generated.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{ StaticCatalogue() }}
    }}
}}

@Composable
private fun StaticCatalogue() {{
    MaterialTheme {{
        Column(modifier = Modifier.padding(24.dp)) {{
            Text({title}, style = MaterialTheme.typography.headlineSmall)
            listOf(
                {quoted}
            ).forEach {{ Text(it) }}
            Text("Structural shell only; no runtime data operations are implemented.")
        }}
    }}
}}
'''
        semantic_manifest = {
            "schema_version": "1",
            "effects": [item.model_dump(mode="json") for item in plan.effects],
            "effect_bindings": [item.model_dump(mode="json") for item in plan.effect_bindings],
            "consequences": [item.model_dump(mode="json") for item in plan.consequences],
        }
        files = {
            "settings.gradle.kts": (
                'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n'
                'dependencyResolutionManagement { repositories { google(); mavenCentral() } }\n'
                'rootProject.name = "esap-android-structural"\ninclude(":app")\n'
            ),
            "build.gradle.kts": (
                'plugins { id("com.android.application") version "8.7.3" apply false; '
                'id("org.jetbrains.kotlin.android") version "2.0.21" apply false; '
                'id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false }\n'
            ),
            "gradle.properties": "android.useAndroidX=true\n",
            "app/build.gradle.kts": (
                'plugins { id("com.android.application"); id("org.jetbrains.kotlin.android"); '
                'id("org.jetbrains.kotlin.plugin.compose") }\n'
                'android { namespace = "generated.app"; compileSdk = 35; '
                'defaultConfig { applicationId = "generated.app"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "0.1" } }\n'
                'dependencies { implementation("androidx.activity:activity-compose:1.9.3"); '
                'implementation(platform("androidx.compose:compose-bom:2024.10.01")); '
                'implementation("androidx.compose.material3:material3") }\n'
            ),
            "app/src/main/AndroidManifest.xml": (
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
                '<application android:label="ESAP structural shell" '
                'android:theme="@android:style/Theme.Material.Light.NoActionBar">'
                '<activity android:name=".MainActivity" android:exported="true">'
                '<intent-filter><action android:name="android.intent.action.MAIN"/>'
                '<category android:name="android.intent.category.LAUNCHER"/></intent-filter>'
                '</activity></application></manifest>\n'
            ),
            "app/src/main/java/generated/app/MainActivity.kt": source,
            "Dockerfile": (
                "FROM eclipse-temurin:17-jdk\n"
                "WORKDIR /workspace\n"
                "RUN echo 'Android builds require the Android SDK and Gradle toolchain.'\n"
            ),
            "k8s/deployment.yaml": (
                "apiVersion: v1\nkind: ConfigMap\nmetadata:\n"
                "  name: android-artifact-boundary\ndata:\n"
                "  workload: native-android-apk-not-a-server-deployment\n"
            ),
            ".github/workflows/android-structural.yml": (
                "name: Android structural source checks\n"
                "on: [pull_request]\n"
                "jobs:\n  source-check:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - uses: actions/checkout@v4\n"
                "      - run: python -m pytest -q tests/test_android_campaign_backend.py\n"
            ),
            "README.md": (
                "# Android structural candidate\n\n"
                "Generated from the campaign CompilationPlan. This is a static "
                "catalogue shell, not a CRUD application. Gradle buildability, "
                "emulator behavior, persistence, validation, search, offline "
                "operation, and lifecycle behavior are not certified.\n"
            ),
            "docs/runtime-boundary.md": (
                "# Runtime boundary\n\n"
                "No repository, persistence engine, CRUD handler, validation "
                "pipeline, search implementation, or offline synchronization "
                "is emitted. A build or launch cannot establish those properties.\n"
            ),
            "docs/architecture.md": (
                "# Architecture\n\n"
                "The backend accepts a campaign CompilationPlan and emits a "
                "static Kotlin Compose catalogue. It refuses service, event, "
                "security, API, effect, consequence, invariant, and frontend "
                "interaction declarations before writing files.\n"
            ),
            "docs/semantic-obligations.json": json.dumps(
                semantic_manifest, sort_keys=True, indent=2
            ) + "\n",
        }
        return build_repository(files)

    def conformance(
        self, plan: CompilationPlan, repo: GeneratedRepository
    ) -> ConformanceReport:
        return CHECKER.check(plan, self.element_paths(plan), repo)


def compile_isr_revision(revision: ISRRevision) -> AndroidCandidate:
    """Authoritative source-bound entrypoint: ISRRevision -> plan -> candidate."""
    plan = isr_to_plan(revision)
    plan_bytes = json.dumps(
        plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    plan_hash = hashlib.sha256(plan_bytes).hexdigest()
    repository = AndroidStructuralBackend().compile(plan)
    return AndroidCandidate(
        revision_hash=revision.content_hash,
        plan_hash=plan_hash,
        repository=repository,
    )
