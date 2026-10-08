"""Evidence-bound documentation generation and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class DocumentationClaim:
    claim: str
    source: str


@dataclass(frozen=True)
class DocumentationValidation:
    passed: bool
    blockers: tuple[str, ...]
    claims: tuple[DocumentationClaim, ...]


def validate_generated_documentation(
    *,
    readme: str,
    system_name: str,
    required_capabilities: Sequence[str] = (),
    selected_frontend: str | None = None,
    selected_backend: str | None = None,
    generated_paths: Sequence[str] = (),
) -> DocumentationValidation:
    """Reject documentation that is malformed, contradictory, or unverifiable."""
    blockers: list[str] = []
    claims: list[DocumentationClaim] = []

    if not readme.strip():
        blockers.append("DOCUMENTATION_EMPTY")
    if not system_name.strip():
        blockers.append("SYSTEM_NAME_MISSING")
    elif f"# {system_name}" not in readme:
        blockers.append("SYSTEM_NAME_MISMATCH")
    else:
        claims.append(DocumentationClaim(f"system_name={system_name}", "ISR"))

    lowered = readme.lower()
    if "lorem ipsum" in lowered or "todo" in lowered or "tbd" in lowered:
        blockers.append("PLACEHOLDER_DOCUMENTATION")

    if "generated from the technology-neutral isr" not in lowered:
        blockers.append("PROVENANCE_MISSING")

    for capability in required_capabilities:
        if capability not in readme:
            blockers.append(f"CAPABILITY_UNDOCUMENTED:{capability}")
        else:
            claims.append(DocumentationClaim(f"capability={capability}", "ISR"))

    if selected_frontend and selected_frontend.lower() not in lowered:
        blockers.append("FRONTEND_CLAIM_MISMATCH")
    if selected_backend and selected_backend.lower() not in lowered:
        blockers.append("BACKEND_CLAIM_MISMATCH")

    # Documentation may describe generated artifacts, but must not assert
    # deployment/runtime success unless those claims are backed by evidence.
    unsupported = re.findall(
        r"(?im)^.*\b(deployed successfully|production ready|all tests pass|fully secure)\b.*$",
        readme,
    )
    if unsupported:
        blockers.append("UNVERIFIED_RUNTIME_CLAIM")

    for path in generated_paths:
        if path not in readme:
            # Paths are only required when the documentation explicitly claims
            # an artifact inventory; this prevents inventing files silently.
            continue

    return DocumentationValidation(
        passed=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        claims=tuple(claims),
    )
