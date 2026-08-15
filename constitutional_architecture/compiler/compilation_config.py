from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


class OptimizationLevel(str, Enum):
    NONE = "none"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"

    @property
    def value(self) -> int:
        return {"none": 0, "standard": 1, "aggressive": 2}[self._value_]


@dataclass(frozen=True)
class CompilationConfig:
    project_name: str
    target_backends: tuple[str, ...] = ("fastapi",)
    output_dir: str = "./generated"
    package_name: str = ""
    optimization_level: OptimizationLevel = OptimizationLevel.STANDARD
    source_maps: bool = True
    generate_tests: bool = True
    generate_docker: bool = True
    capability_hints: dict[str, str] = field(default_factory=dict)
    compiler_version: str = "1.0.0"
    verbose: bool = False

    def __post_init__(self) -> None:
        if not self.package_name:
            object.__setattr__(self, "package_name",
                               self.project_name.lower().replace("-", "_").replace(" ", "_"))

    @property
    def config_hash(self) -> str:
        canonical = json.dumps({
            "project_name": self.project_name,
            "target_backends": sorted(self.target_backends),
            "optimization_level": self.optimization_level.value,
            "source_maps": self.source_maps,
            "generate_tests": self.generate_tests,
            "generate_docker": self.generate_docker,
            "compiler_version": self.compiler_version,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
