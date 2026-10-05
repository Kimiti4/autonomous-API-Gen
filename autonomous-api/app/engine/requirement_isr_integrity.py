"""Fail-closed integrity checks for the Engineering ISR.

The ISR is a derived authority boundary: it may constrain downstream work but
must never invent requirements, dangling traces, duplicate identities, or
implementation technology choices.
"""
from __future__ import annotations

from dataclasses import dataclass

from .requirement_isr import EngineeringISR


@dataclass(frozen=True)
class ISRIntegrityReport:
    valid: bool
    errors: tuple[str, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise ValueError("invalid-engineering-isr:" + ",".join(self.errors))


FORBIDDEN_TECHNOLOGY_TOKENS = (
    "postgres", "postgresql", "redis", "kafka", "fastapi", "react",
    "docker", "kubernetes", "aws", "azure", "gcp", "rust", "python",
    "typescript", "javascript",
)


def validate_isr_integrity(isr: EngineeringISR) -> ISRIntegrityReport:
    errors: list[str] = []
    sources = set(isr.source_requirement_ids)
    if len(isr.source_requirement_ids) != len(sources):
        errors.append("duplicate-source-requirement")
    for collection_name, items, id_attr in (
        ("entities", isr.entities, "entity_id"),
        ("invariants", isr.invariants, "invariant_id"),
        ("policies", isr.policies, "policy_id"),
        ("interfaces", isr.interfaces, "interface_id"),
    ):
        ids = [getattr(item, id_attr) for item in items]
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate-{collection_name}-id")
        for item in items:
            for rid in item.source_requirements:
                if rid not in sources:
                    errors.append(f"dangling-source:{rid}")
            text = " ".join(str(v) for v in vars(item).values()).lower()
            if any(token in text for token in FORBIDDEN_TECHNOLOGY_TOKENS):
                errors.append(f"technology-leak:{collection_name}:{getattr(item, id_attr)}")
    for rid in isr.traceability:
        if rid not in sources:
            errors.append(f"dangling-traceability:{rid}")
    if set(isr.traceability) != sources:
        errors.append("incomplete-traceability")
    return ISRIntegrityReport(not errors, tuple(sorted(set(errors))))
