"""Deterministic, provider-free analysis of structured ESAP acceptance contracts.

This module does not generate application code or infer missing intent. It converts
a structured acceptance contract into a traceable work ledger. Capability items remain
unsupported until a callable compiler handler is explicitly registered.
Only the Python standard library is required; this module performs no network calls.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping


VALID_STATUSES = {"supported", "unsupported", "ambiguous", "unknown"}


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    kind: str
    name: str
    status: str
    source: str
    detail: str

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid requirement status: {self.status}")


@dataclass(frozen=True)
class Analysis:
    project_id: str
    contract_digest: str
    requirements: tuple[Requirement, ...]

    def as_dict(self) -> dict[str, Any]:
        counts = {status: 0 for status in sorted(VALID_STATUSES)}
        for item in self.requirements:
            counts[item.status] += 1
        return {
            "schema_version": "1.0",
            "project_id": self.project_id,
            "contract_sha256": self.contract_digest,
            "provider_required": False,
            "network_calls": 0,
            "requirements": [asdict(item) for item in self.requirements],
            "status_counts": counts,
            "certified": False,
            "certification_note": (
                "Analysis only: no code was generated and no quality gate was executed."
            ),
        }


def _stable_id(kind: str, name: str) -> str:
    raw = f"{kind}:{name}".encode("utf-8")
    return f"REQ-{hashlib.sha256(raw).hexdigest()[:12].upper()}"


def analyze_acceptance(
    acceptance: Mapping[str, Any],
    *,
    capability_handlers: Mapping[str, Callable[..., Any]] | None = None,
    source: str = "golden-projects/taskflow/ACCEPTANCE.json",
) -> Analysis:
    """Analyze structured acceptance data without models, plugins, or network access.

    A capability is marked supported only when a callable compiler handler is
    explicitly registered for that capability. Registration is not certification:
    the generated result still requires independent verification. Quality gates and
    negative cases start UNKNOWN because this function does not execute them.
    """
    if not isinstance(acceptance, Mapping):
        raise TypeError("Acceptance contract must be a JSON object")

    project_id = acceptance.get("project_id", "UNSPECIFIED")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")

    capabilities = acceptance.get("required_capabilities", [])
    if not isinstance(capabilities, list) or any(
        not isinstance(item, str) or not item.strip() for item in capabilities
    ):
        raise ValueError("required_capabilities must be a list of non-empty strings")
    if len(set(capabilities)) != len(capabilities):
        raise ValueError("required_capabilities contains duplicates")

    gates = acceptance.get("quality_gates", {})
    if not isinstance(gates, Mapping) or any(
        not isinstance(name, str) or not isinstance(enabled, bool)
        for name, enabled in gates.items()
    ):
        raise ValueError("quality_gates must map names to boolean values")

    negative_cases = acceptance.get("negative_cases", [])
    if not isinstance(negative_cases, list) or any(
        not isinstance(item, str) or not item.strip() for item in negative_cases
    ):
        raise ValueError("negative_cases must be a list of non-empty strings")
    if len(set(negative_cases)) != len(negative_cases):
        raise ValueError("negative_cases contains duplicates")

    handlers = capability_handlers or {}
    if not isinstance(handlers, Mapping):
        raise TypeError("capability_handlers must be a mapping")
    unknown_handlers = set(handlers).difference(capabilities)
    if unknown_handlers:
        raise ValueError(
            "Capability registry contains names absent from the contract: "
            + ", ".join(sorted(unknown_handlers))
        )
    invalid_handlers = [
        name for name, handler in handlers.items() if not callable(handler)
    ]
    if invalid_handlers:
        raise TypeError(
            "Capability registry entries must be callable: "
            + ", ".join(sorted(invalid_handlers))
        )

    requirements: list[Requirement] = []
    for name in capabilities:
        status = "unknown" if name in handlers else "unsupported"
        requirements.append(
            Requirement(
                requirement_id=_stable_id("capability", name),
                kind="capability",
                name=name,
                status=status,
                source=source,
                detail=(
                    "A callable compiler handler is registered, but capability evidence is not yet verified."
                    if status == "supported"
                    else "No provider-free compiler handler is registered."
                ),
            )
        )

    for name, enabled in sorted(gates.items()):
        if enabled:
            requirements.append(
                Requirement(
                    requirement_id=_stable_id("quality_gate", name),
                    kind="quality_gate",
                    name=name,
                    status="unknown",
                    source=source,
                    detail="Required gate has not been executed by acceptance analysis.",
                )
            )

    for name in negative_cases:
        requirements.append(
            Requirement(
                requirement_id=_stable_id("negative_case", name),
                kind="negative_case",
                name=name,
                status="unknown",
                source=source,
                detail="Negative case requires an executable test and observed result.",
            )
        )

    canonical = json.dumps(
        acceptance, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return Analysis(
        project_id=project_id,
        contract_digest=hashlib.sha256(canonical).hexdigest(),
        requirements=tuple(requirements),
    )
