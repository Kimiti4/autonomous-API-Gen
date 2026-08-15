"""Static coupling scanner for the domain layer.

Scans pydantic model field names, field defaults, and str-enum member values
for technology tokens (Cap-A denylist) and implementation-detail tokens.
Production code, not test-only: reusable from CI and future boundary audits.
"""

from __future__ import annotations

import enum
import importlib
import pkgutil
import re
from typing import Any, Iterator

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from ..models.system_model import TECHNOLOGY_TOKENS
from .coupling_registry import CouplingCategory

#: Curated implementation-detail tokens. Curation rule: unambiguous
#: deployment/transport mechanics that never belong in an abstract ISR.
IMPLEMENTATION_DETAIL_TOKENS: tuple[str, ...] = ("port",)

_TECH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE))
    for token in TECHNOLOGY_TOKENS
)
_IMPL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE))
    for token in IMPLEMENTATION_DETAIL_TOKENS
)


class CouplingFinding(BaseModel):
    qualified_path: str
    category: CouplingCategory
    matched_token: str
    evidence: str


def iter_strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")


def _match_name(text: str) -> tuple[CouplingCategory, str] | None:
    """Match a field name or enum member against both token sets."""
    for token, pattern in _TECH_PATTERNS:
        if pattern.search(text):
            return CouplingCategory.TECHNOLOGY_TOKEN_FIELD_NAME, token
    for token, pattern in _IMPL_PATTERNS:
        if pattern.search(text):
            return CouplingCategory.IMPLEMENTATION_DETAIL_FIELD, token
    return None


def _match_value(text: str) -> str | None:
    """Match a default value string against technology tokens only."""
    for token, pattern in _TECH_PATTERNS:
        if pattern.search(text):
            return token
    return None


def _resolve_default(field_info: Any) -> Any:
    if field_info.default is not PydanticUndefined:
        return field_info.default
    if field_info.default_factory is not None:  # type: ignore[misc]
        return field_info.default_factory()
    return None


def scan_model_class(cls: type[BaseModel]) -> list[CouplingFinding]:
    findings: list[CouplingFinding] = []
    for field_name, field_info in cls.model_fields.items():
        name_hit = _match_name(field_name)
        if name_hit is not None:
            category, token = name_hit
            findings.append(
                CouplingFinding(
                    qualified_path=f"{cls.__module__}.{cls.__name__}.{field_name}",
                    category=category,
                    matched_token=token,
                    evidence=f"field name '{field_name}'",
                )
            )
        default = _resolve_default(field_info)
        if default is not None:
            for _path, text in iter_strings(default):
                token = _match_value(text)
                if token is not None:
                    findings.append(
                        CouplingFinding(
                            qualified_path=f"{cls.__module__}.{cls.__name__}.{field_name}",
                            category=CouplingCategory.TECHNOLOGY_TOKEN_DEFAULT_VALUE,
                            matched_token=token,
                            evidence=f"default value contains '{text[:80]}'",
                        )
                    )
    return findings


def scan_enum_class(cls: type[enum.Enum]) -> list[CouplingFinding]:
    findings: list[CouplingFinding] = []
    for member in cls:
        if not isinstance(member.value, str):
            continue
        for token, pattern in _TECH_PATTERNS:
            if pattern.search(member.value):
                findings.append(
                    CouplingFinding(
                        qualified_path=f"{cls.__module__}.{cls.__name__}.{member.name}",
                        category=CouplingCategory.TECHNOLOGY_TOKEN_ENUM_VALUE,
                        matched_token=token,
                        evidence=f"enum value '{member.value}'",
                    )
                )
    return findings


def scan_domain_models(root: str = "tiannara.domain") -> list[CouplingFinding]:
    """Scan every model and enum defined under ``root``."""
    findings: list[CouplingFinding] = []
    package = importlib.import_module(root)
    modules = [package]
    for info in pkgutil.walk_packages(package.__path__, prefix=f"{root}."):
        modules.append(importlib.import_module(info.name))
    for module in modules:
        for value in vars(module).values():
            if not isinstance(value, type):
                continue
            if not getattr(value, "__module__", "").startswith(root):
                continue  # imported, not defined here
            if isinstance(value, type(BaseModel)) and issubclass(value, BaseModel):
                findings.extend(scan_model_class(value))
            elif issubclass(value, enum.Enum):
                findings.extend(scan_enum_class(value))
    return sorted(
        findings,
        key=lambda f: (f.qualified_path, f.category.value, f.matched_token),
    )
