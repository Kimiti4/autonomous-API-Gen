from pydantic import BaseModel, Field

try:
    import yaml  # type: ignore
except Exception:  # PyYAML optional; JSON manifests always work.
    yaml = None  # type: ignore


class ProjectEntry(BaseModel):
    id: str
    intent: str
    domain: str
    target_backend: str = "minimal-container"
    complexity_tier: str = "medium"
    constraints: dict[str, str] = Field(default_factory=dict)


class StratifiedManifest(BaseModel):
    """Declarative stratification of the calibration matrix (never hardcoded
    into the execution loop)."""

    projects: list[ProjectEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, path) -> "StratifiedManifest":
        path = str(path)
        text = open(path, encoding="utf-8").read()
        if path.endswith((".yaml", ".yml")) and yaml is not None:
            data = yaml.safe_load(text)
        else:
            import json
            data = json.loads(text)
        return cls(projects=[p if isinstance(p, ProjectEntry) else ProjectEntry(**p) for p in data.get("projects", [])])

    @property
    def size(self) -> int:
        return len(self.projects)
