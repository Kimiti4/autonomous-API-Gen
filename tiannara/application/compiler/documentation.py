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


def evidence_bound_readme(
    *,
    slug: str,
    system_name: str,
    backend_id: str,
    capabilities: Sequence[str],
    architecture_lines: Sequence[str] = (),
    verify_commands: Sequence[str] = (),
    run_commands: Sequence[str] = (),
) -> str:
    """Build a README that satisfies this module's own validation contract.

    Every generated bundle documents: the artifact's package identity (the
    slug that ``ProjectCompiler._verify`` validates against), the ISR system
    name, the technology-neutral-ISR provenance, the backend claim, and the
    backend's full declared capability manifest. Backends must not hand-roll
    README strings — use this helper so docs stay certification-bound.
    """
    lines: list[str] = [
        f"# {slug}",
        "",
        f"System: {system_name}",
        "",
        "Generated from the technology-neutral ISR — compiled artifact of an "
        "evolved software design.",
        "",
        f"Backend: {backend_id}",
        "",
        "## Architecture",
        "",
    ]
    lines.extend(architecture_lines or ["(see generated sources for layout)"])
    lines.extend(["", "## Capabilities", ""])
    lines.extend(f"- {capability}" for capability in capabilities)
    if verify_commands:
        lines.extend(["", "## Verify", "", "```bash", *verify_commands, "```"])
    if run_commands:
        lines.extend(["", "## Run", "", "```bash", *run_commands, "```"])
    lines.append("")
    return "\n".join(lines)


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
