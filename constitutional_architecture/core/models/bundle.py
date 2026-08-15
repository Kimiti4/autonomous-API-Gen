from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    TEST_SUITE = "test_suite"
    DOCKERFILE = "dockerfile"
    CI_CD_PIPELINE = "ci_cd_pipeline"
    DATABASE_MIGRATION = "database_migration"
    SDK_CLIENT = "sdk_client"


class CompilationManifest(BaseModel):
    artifact_type: ArtifactType
    domain: str
    files: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompilationBundle(BaseModel):
    compiler_id: str
    target_technology: str
    manifests: List[CompilationManifest] = Field(default_factory=list)
    requires_bundles: List[str] = Field(default_factory=list)
    exposed_interfaces: Dict[str, Any] = Field(default_factory=dict)


class SystemDeploymentBundle(BaseModel):
    project_name: str
    bundles: Dict[str, CompilationBundle] = Field(default_factory=dict)
    global_metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_all_files(self) -> Dict[str, str]:
        all_files: Dict[str, str] = {}
        for bundle in self.bundles.values():
            for manifest in bundle.manifests:
                for path, content in manifest.files.items():
                    full_path = f"{bundle.target_technology}/{manifest.domain}/{path}"
                    all_files[full_path] = content
        return all_files
