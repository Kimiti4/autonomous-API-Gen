"""R2.10.3-I — the documentation-intent mutation operator (gene-level mutation).

``DocumentationOperator`` mutates the documentation gene class alone
(System.documentation_intents): add/remove/respecify/generate. It never
touches behavior, capability, requirement, acceptance-criterion, migration,
temporal, reliability, boundary, deployment, testing-anchor, or entity
genes.

Non-authority is structural: documentation references its subjects by
identity and can never define, override, or feed back into them — there is
no mechanism in the construct to author anything but its own intent.
Locality is proven both ways: changing documentation moves only the
documentation gene; a subject's implementation evolves while the
documentation gene holds.

No operator here can attach a realization (format, template, path,
generator), because the construct has no field for one and the
DOCUMENTATION_MECHANISM_TERMS lint gates the semantic form.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    DocumentationAudience,
    DocumentationIntent,
    DocumentationPurpose,
    DocumentationValidationError,
    ISR,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class DocumentationOperator:
    """Mutates only the documentation gene class (System.documentation_intents)."""

    operator_id = "documentation"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_intents(isr: ISR, intents: Sequence[DocumentationIntent]) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, documentation_intents=tuple(intents))
        )

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        subject_id: str,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "documentation",
                        "operation": operation,
                        "subject_id": subject_id,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{DocumentationOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=DocumentationOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"documentation: {operation} '{subject_id}'",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        subject_id: str,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-i",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=subject_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "subject_id": subject_id,
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-i")

    # -- operations -----------------------------------------------------------------

    def add_documentation(
        self, isr: ISR, intent: DocumentationIntent
    ) -> MutationCandidate:
        """Declare one documentation intent — nothing else changes."""
        existing = {d.documentation_id for d in isr.system.documentation_intents}
        if intent.documentation_id in existing:
            raise DocumentationValidationError(
                f"documentation '{intent.documentation_id}' already declared"
            )
        after = self._replace_intents(
            isr, isr.system.documentation_intents + (intent,)
        )
        self._attest(isr, after, "add_documentation", intent.documentation_id)
        return self._candidate(isr, after, "add_documentation", intent.documentation_id)

    def remove_documentation(
        self, isr: ISR, *, documentation_id: str
    ) -> MutationCandidate:
        """Remove one documentation intent; removal restores the exact prior
        hash when the intent was the only one."""
        for intent in isr.system.documentation_intents:
            if intent.documentation_id == documentation_id:
                after = self._replace_intents(
                    isr,
                    tuple(
                        d
                        for d in isr.system.documentation_intents
                        if d.documentation_id != documentation_id
                    ),
                )
                self._attest(isr, after, "remove_documentation", documentation_id)
                return self._candidate(
                    isr, after, "remove_documentation", documentation_id
                )
        raise DocumentationValidationError(
            f"documentation '{documentation_id}' not found"
        )

    def respecify_documentation(
        self,
        isr: ISR,
        *,
        documentation_id: str,
        purpose: Optional[DocumentationPurpose] = None,
        audience: Optional[DocumentationAudience] = None,
        obligations: Optional[tuple[str, ...]] = None,
        subject_refs: Optional[tuple[str, ...]] = None,
    ) -> MutationCandidate:
        """Respecify the documentation intent; every unset dimension is
        untouched.

        Reference-by-identity, backwards: the subject genes this intent
        references by id do NOT move. Documentation may respecify WHAT it
        documents (subject_refs), but never WHAT those subjects are.
        """
        for intent in isr.system.documentation_intents:
            if intent.documentation_id == documentation_id:
                edited = dataclasses.replace(
                    intent,
                    purpose=purpose if purpose is not None else intent.purpose,
                    audience=audience if audience is not None else intent.audience,
                    obligations=(
                        obligations if obligations is not None else intent.obligations
                    ),
                    subject_refs=(
                        subject_refs if subject_refs is not None else intent.subject_refs
                    ),
                )
                after = self._replace_intents(
                    isr,
                    tuple(
                        edited if d.documentation_id == documentation_id else d
                        for d in isr.system.documentation_intents
                    ),
                )
                self._attest(isr, after, "respecify_documentation", documentation_id)
                return self._candidate(
                    isr, after, "respecify_documentation", documentation_id
                )
        raise DocumentationValidationError(
            f"documentation '{documentation_id}' not found"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the documentation gene class.

        Deterministic by construction: candidates document the first
        ``population_size`` sorted workflows as OPERATIONAL_REFERENCE for
        DEVELOPERs — no randomness, ``seed`` accepted for protocol
        compatibility and reproducibility attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        workflow_ids = sorted(
            w.id for m in isr.system.modules for w in m.workflows
        )
        for i in range(min(len(workflow_ids), population_size)):
            intent = DocumentationIntent(
                documentation_id=f"doc.{workflow_ids[i]}",
                subject_refs=(workflow_ids[i],),
                purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
                audience=DocumentationAudience.DEVELOPER,
                obligations=("the workflow's declared behavior must be documented",),
            )
            candidates.append(self.add_documentation(isr, intent))
        return tuple(candidates)