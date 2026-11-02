"""Conservative Android application backend.

The backend deliberately supports only a static, model-derived Android shell.
It refuses service/API/event semantics rather than silently dropping runtime
behaviour. It does not claim persistence, authentication, synchronization,
CRUD, or network capabilities.
"""
from __future__ import annotations

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.domain.models.backend_declaration import ArtifactKind, BackendCapabilityDeclaration
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.system_model import SystemModel
from .naming import pascal_case, slugify


class AndroidBackend:
    backend_id = "android"

    @property
    def name(self) -> str:
        return self.backend_id

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        return BackendBuildProfile(
            language="kotlin",
            required_files=(
                "settings.gradle.kts",
                "build.gradle.kts",
                "app/build.gradle.kts",
                "app/src/main/AndroidManifest.xml",
                "app/src/main/java/generated/app/MainActivity.kt",
            ),
            verifier_kind="android",
            build_command=["gradle", ":app:assembleDebug", "--no-daemon"],
            test_command=None,
            requires_build_phase=True,
        )

    def build_profile_declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],
            capabilities=[BundleCapability.BUILD, BundleCapability.DOCUMENTATION],
            quality_profile=0.55,
            metadata={"language": "kotlin", "platform": "android", "scope": "static-model-shell"},
        )

    def generate(self, model: SystemModel) -> CompilationResult:
        if not model.data_models:
            raise ValueError("android backend requires at least one declared data model")
        if model.services or model.apis or model.events:
            raise ValueError(
                "android backend currently refuses service, API, and event semantics; "
                "no runtime behaviour may be silently omitted"
            )
        package = "generated.app"
        slug = slugify(model.system_name)
        model_names = [pascal_case(item.name) for item in model.data_models]
        labels = ", ".join(f'"{name}"' for name in model_names)
        source = f'''package {package}

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{ GeneratedApplication() }}
    }}
}}

@Composable
private fun GeneratedApplication() {{
    MaterialTheme {{
        Surface(modifier = Modifier.fillMaxSize()) {{
            Column(
                modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {{
                Text("{self._kotlin_string(model.system_name)}", style = MaterialTheme.typography.headlineSmall)
                Text("Generated model catalogue", style = MaterialTheme.typography.titleMedium)
                listOf({labels}).forEach {{ name ->
                    Text(name, style = MaterialTheme.typography.bodyLarge)
                }}
                Text("Static shell only — no persistence, authentication, or synchronization is implemented.")
            }}
        }}
    }}
}}
'''
        files = {
            "settings.gradle.kts": 'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\ndependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\nrootProject.name = "' + slug + '"\ninclude(":app")\n',
            "build.gradle.kts": 'plugins { id("com.android.application") version "8.7.3" apply false; id("org.jetbrains.kotlin.android") version "2.0.21" apply false; id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false }\n',
            "gradle.properties": "org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\nkotlin.code.style=official\n",
            "app/build.gradle.kts": '''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "generated.app"
    compileSdk = 35
    defaultConfig { applicationId = "generated.app"; minSdk = 23; targetSdk = 35; versionCode = 1; versionName = "1.0" }
}
dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    testImplementation("junit:junit:4.13.2")
}
''',
            "app/src/main/AndroidManifest.xml": '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="Generated application" android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
        </activity>
    </application>
</manifest>
''',
            "app/src/main/java/generated/app/MainActivity.kt": source,
            "README.md": f"# {model.system_name}\n\nGenerated from SystemModel {model.content_hash()}.\n\nThis backend currently emits a buildable static Android model catalogue only. It does not implement persistence, CRUD, authentication, synchronization, or service/API/event behaviour. Such semantics are rejected rather than omitted.\n",
        }
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slug,
            files=files,
            capability_manifest=CapabilityManifest(
                backend_id=self.backend_id,
                capabilities=[BundleCapability.BUILD, BundleCapability.DOCUMENTATION],
                metadata={"platform": "android", "scope": "static-model-shell", "runtime_features": []},
            ),
        )

    @staticmethod
    def _kotlin_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
