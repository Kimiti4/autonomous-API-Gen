"""Evidence-derived documentation manifest for certified ESAP software."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DocumentationSection:
    section_id: str
    title: str
    content: str
    evidence_ids: tuple[str, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class DocumentationManifest:
    project_id: str
    certification_digest: str
    sections: tuple[DocumentationSection, ...]
    certified_only: bool = True


def build_documentation_manifest(
    *,
    project_id: str,
    certification_digest: str,
    sections: tuple[DocumentationSection, ...],
    certified: bool,
) -> DocumentationManifest:
    if not certified:
        raise ValueError("documentation-requires-certified-project")
    if not project_id.strip() or not certification_digest.strip():
        raise ValueError("documentation-requires-certification-identity")
    for section in sections:
        if not section.content.strip():
            raise ValueError(f"documentation-empty-section:{section.section_id}")
        if not section.evidence_ids:
            raise ValueError(f"documentation-missing-evidence:{section.section_id}")
        if not section.source_ids:
            raise ValueError(f"documentation-missing-sources:{section.section_id}")
    return DocumentationManifest(project_id, certification_digest, sections)


def validate_documentation_manifest(
    manifest: DocumentationManifest,
    current_evidence_ids: set[str],
    current_source_ids: set[str],
) -> tuple[str, ...]:
    errors=[]
    if not manifest.certified_only:
        errors.append("documentation-not-certified-only")
    for section in manifest.sections:
        if not set(section.evidence_ids) <= current_evidence_ids:
            errors.append(f"stale-evidence:{section.section_id}")
        if not set(section.source_ids) <= current_source_ids:
            errors.append(f"stale-source:{section.section_id}")
    return tuple(sorted(set(errors)))
