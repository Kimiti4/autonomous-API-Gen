"""Bidirectional guard: the domain layer's coupling must exactly equal the
registry. Unregistered coupling fails; stale registry entries fail."""

import enum
import importlib

from pydantic import BaseModel

from tiannara.domain.governance.coupling_registry import (
    LEGACY_COUPLING_REGISTRY,
    CouplingCategory,
)
from tiannara.domain.governance.coupling_scanner import (
    scan_domain_models,
    scan_enum_class,
    scan_model_class,
)


class _DirtyModel(BaseModel):
    redis: str = "events"       # field name 'redis' -> tech token field name
    port: int = 8080           # field name 'port' -> impl detail field
    cache: str = "redis"       # default value 'redis' -> tech token default value


class _DirtyEnum(str, enum.Enum):
    primary = "postgresql"


def test_scanner_detects_field_name_tokens():
    findings = scan_model_class(_DirtyModel)
    tokens = {(f.matched_token, f.category) for f in findings}
    assert ("redis", CouplingCategory.TECHNOLOGY_TOKEN_FIELD_NAME) in tokens
    assert ("port", CouplingCategory.IMPLEMENTATION_DETAIL_FIELD) in tokens


def test_scanner_detects_default_value_tokens():
    findings = scan_model_class(_DirtyModel)
    assert any(
        f.matched_token == "redis"
        and f.category is CouplingCategory.TECHNOLOGY_TOKEN_DEFAULT_VALUE
        for f in findings
    )


def test_scanner_detects_enum_value_tokens():
    findings = scan_enum_class(_DirtyEnum)
    assert findings[0].matched_token == "postgresql"
    assert findings[0].category is CouplingCategory.TECHNOLOGY_TOKEN_ENUM_VALUE


def test_registry_exactly_matches_domain_scan():
    findings = scan_domain_models()
    found = {
        (f.qualified_path, f.category, f.matched_token) for f in findings
    }
    registered = {
        (e.qualified_path, e.category, e.matched_token)
        for e in LEGACY_COUPLING_REGISTRY
    }

    unregistered = found - registered
    assert not unregistered, (
        "New constitutional debt detected. Fix the design -- do not register "
        f"new debt. Unregistered: {sorted(unregistered)}"
    )

    stale = registered - found
    assert not stale, (
        "Registry entries no longer found: debt was paid off or moved. "
        f"Update the registry. Stale: {sorted(stale)}"
    )


def test_registry_paths_resolve():
    """Every registered path must point at a real field (typo guard)."""
    for entry in LEGACY_COUPLING_REGISTRY:
        parts = entry.qualified_path.split(".")
        field_name = parts[-1]
        class_name = parts[-2]
        module_name = ".".join(parts[:-2])
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        assert field_name in getattr(cls, "model_fields", {}), (
            f"registry path does not resolve to a model field: "
            f"{entry.qualified_path}"
        )
