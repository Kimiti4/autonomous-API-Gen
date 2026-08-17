"""R2.10.3-I — documentation primitive (intent, never artifact).

Documentation as an ISR-owned SEMANTIC artifact — NOT generated Markdown,
HTML, source comments, or diagrams. A DocumentationIntent declares what must
be documented, for whom, and why; the realization (Markdown, HTML, API docs,
diagrams, anything else) is a compiler/backend concern and never part of
this primitive. The structural field guard leaves nowhere to put a format
or a path, and DOCUMENTATION_MECHANISM_TERMS gates the canonical semantic
form.

Direction is one-way: **ISR semantics → documentation intent → realization**.
Documentation references its subjects by identity; it never defines,
overrides, or feeds back into them — it cannot become a second source of
truth because it has no mechanism to author anything but its own intent.
That non-authority is structural: the construct carries no override /
redefine / replace / author field, and locality is proven both ways —
changing documentation moves only the documentation gene; a subject's
implementation can evolve while the documentation gene holds.

I is deliberately small: five fields, two enums, one lint. `coverage_refs`
collapses into `subject_refs`; an `evolution_policy` would only ever have
one valid value (derived), because the non-authority constraint makes
documentation inherently non-authoritative. Both are future extensions if a
concrete substrate needs them — complexity must always provide measurable
architectural value.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class DocumentationValidationError(ValueError):
    """A documentation intent violates its construction or structural contract."""


@unique
class DocumentationPurpose(str, Enum):
    """WHY this documentation exists — semantic, never a format."""

    OPERATIONAL_REFERENCE = "OPERATIONAL_REFERENCE"
    ARCHITECTURAL_RATIONALE = "ARCHITECTURAL_RATIONALE"
    API_CONTRACT = "API_CONTRACT"
    ONBOARDING = "ONBOARDING"
    COMPLIANCE = "COMPLIANCE"


@unique
class DocumentationAudience(str, Enum):
    """WHO this documentation serves — semantic, never a channel."""

    OPERATOR = "OPERATOR"
    DEVELOPER = "DEVELOPER"
    ARCHITECT = "ARCHITECT"
    SECURITY_AUDITOR = "SECURITY_AUDITOR"
    END_USER = "END_USER"


@dataclass(frozen=True)
class DocumentationIntent:
    """Documentation as an ISR-owned semantic artifact. NOT generated Markdown,
    HTML, or source comments.

    Declares what must be documented, for whom, and why. The realization —
    Markdown, HTML, API docs, diagrams — is a compiler/backend concern and
    never part of this primitive.

    Direction is one-way: ISR semantics → documentation intent → realization.
    Documentation references its subjects by identity; it never defines,
    overrides, or feeds back into them. It cannot become a second source of
    truth because it has no mechanism to author anything but its own intent.
    """

    documentation_id: str
    subject_refs: tuple[str, ...]  # genes being documented (by id)
    purpose: DocumentationPurpose
    audience: DocumentationAudience
    obligations: tuple[str, ...] = ()  # what the documentation must establish

    def __post_init__(self) -> None:
        if not self.documentation_id:
            raise DocumentationValidationError("documentation_id is required")
        if not self.subject_refs:
            raise DocumentationValidationError(
                "subject_refs required: documentation must document something explicit"
            )


# -- mechanism lint (the dangerous boundary — no realization artifacts) ------

DOCUMENTATION_MECHANISM_TERMS: frozenset[str] = frozenset({
    # realization formats
    "markdown", "html", "rst", "mdx", "latex", "asciidoc",
    # realization artifacts
    "template", "filepath", "file_path", "output_path", "render_config",
    # documentation generators / toolchains
    "docusaurus", "mkdocs", "sphinx", "javadoc", "typedoc", "doxygen", "gitbook",
})


def documentation_mechanism_hits(doc: DocumentationIntent) -> tuple[str, ...]:
    """Which realization terms (if any) leaked into a documentation intent."""
    lowered = canonicalize(doc).lower()
    return tuple(term for term in DOCUMENTATION_MECHANISM_TERMS if term in lowered)


def assert_documentation_technology_agnostic(doc: DocumentationIntent) -> None:
    """Gate: no format, path, or generator may leak into the documentation intent.

    ``purpose=OPERATIONAL_REFERENCE, audience=OPERATOR`` passes;
    ``purpose=render_markdown_via_mkdocs`` fails. The intent stays the
    declaration; the backend owns the realization.
    """
    hits = documentation_mechanism_hits(doc)
    if hits:
        raise DocumentationValidationError(
            f"documentation '{doc.documentation_id}' couples to "
            f"realization mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _documentable_gene_ids(system: Any) -> set[str]:
    """The documentation identity space: behaviors (workflow ids),
    capabilities, requirements, modules, and boundaries — anything the ISR
    declares can be documented by identity."""
    ids: set[str] = set()
    for module in system.modules:
        ids.add(module.id)
        ids.update(workflow.id for workflow in module.workflows)
    ids.update(c.capability_id for c in system.business_capabilities)
    ids.update(r.requirement_id for r in system.requirements)
    ids.update(b.boundary_id for b in system.architectural_boundaries)
    return ids


def validate_system_documentation_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's documentation intents.

    Rejects, pre-execution: duplicate documentation ids and dangling subject
    refs (must name behaviors/capabilities/requirements/modules/boundaries).
    Empty tuple means valid.
    """
    errors: list[str] = []
    documentable_ids = _documentable_gene_ids(system)
    seen: set[str] = set()
    for doc in system.documentation_intents:
        if doc.documentation_id in seen:
            errors.append(f"duplicate documentation id '{doc.documentation_id}'")
        seen.add(doc.documentation_id)
        for subject_ref in doc.subject_refs:
            if subject_ref not in documentable_ids:
                errors.append(
                    f"documentation '{doc.documentation_id}' documents unknown "
                    f"gene '{subject_ref}'"
                )
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_documentation_intents(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of documentation intents.

    Returns the documentation declarations (subjects, purpose, audience,
    obligations). Never formats, templates, paths, or generators — those are
    compiler/backend infrastructure, not the intent.
    """
    return tuple(
        canonical_form(doc)
        for doc in getattr(isr.system, "documentation_intents", ())
    )