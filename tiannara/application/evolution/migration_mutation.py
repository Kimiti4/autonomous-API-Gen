"""R2.10.3-C — the migration mutation operator (gene-level mutation).

``MigrationOperator`` mutates the migration gene class alone:
add/remove/set-compatibility-policy/edit-preservation-membership. It never
touches entity, behavior, capability, or temporal genes — the
mutation-locality contract that makes ``data_migrations`` independently
evolvable.

A migration's gene is (compatibility intent, preservation refs, ordering,
rollback semantics, postconditions) — semantic declarations only. No
operator here can attach an execution mechanism, because the construct has
no field for one.

Every mutation is attributed in the ledger as an R2.8.3 MEASUREMENT event.
The operator is deterministic: identical inputs produce identical candidates.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional, Sequence

from constitutional_architecture.isr.model import (
    CompatibilityPolicy,
    DataMigrationIntent,
    ISR,
    MigrationValidationError,
)

from .ledger import EventType, EvolutionEvent, EvolutionLedger, stable_isr_hash
from .mutation_operators import ISRDelta, MutationCandidate


class MigrationOperator:
    """Mutates only the migration gene class (Module.data_migrations)."""

    operator_id = "data_migration"

    def __init__(self, ledger: Optional[EvolutionLedger] = None) -> None:
        self._ledger = ledger

    # -- rebuild helpers ------------------------------------------------------

    @staticmethod
    def _replace_module_migrations(
        isr: ISR, module_id: str, migrations: Sequence[DataMigrationIntent]
    ) -> ISR:
        modules = []
        for module in isr.system.modules:
            if module.id == module_id:
                module = dataclasses.replace(
                    module, data_migrations=tuple(migrations)
                )
            modules.append(module)
        return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))

    @staticmethod
    def _candidate(
        isr: ISR,
        after: ISR,
        operation: str,
        migration: DataMigrationIntent,
    ) -> MutationCandidate:
        delta = ISRDelta(
            (
                json.dumps(
                    {
                        "operator": "data_migration",
                        "operation": operation,
                        "migration_id": migration.migration_id,
                        "source_schema_ref": migration.source_schema_ref,
                        "target_schema_ref": migration.target_schema_ref,
                        "compatibility_policy": migration.compatibility_policy.value,
                    },
                    sort_keys=True,
                ),
            )
        )
        return MutationCandidate(
            candidate_id=f"{MigrationOperator.operator_id}:"
            f"{stable_isr_hash(after)[:12]}",
            operator_id=MigrationOperator.operator_id,
            candidate_isr=after,
            parent_isr=isr,
            mutation_delta=delta,
            hypothesis=f"data_migration: {operation} '{migration.migration_id}' "
            f"({migration.compatibility_policy.value})",
        )

    # -- attribution ------------------------------------------------------------

    def _attest(
        self,
        before: ISR,
        after: ISR,
        operation: str,
        migration: DataMigrationIntent,
    ) -> None:
        if self._ledger is None:
            return
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.10.3-c",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=migration.migration_id,
            isr_hash=stable_isr_hash(after),
            payload={
                "operator_id": self.operator_id,
                "operation": operation,
                "migration_id": migration.migration_id,
                "source_schema_ref": migration.source_schema_ref,
                "target_schema_ref": migration.target_schema_ref,
                "compatibility_policy": migration.compatibility_policy.value,
                "rollback_required": migration.rollback_required,
                "isr_hash_before": stable_isr_hash(before),
                "isr_hash_after": stable_isr_hash(after),
            },
        )
        self._ledger.append_event(event, evolution_id="r2.10.3-c")

    # -- operations -----------------------------------------------------------------

    def add_migration(
        self, isr: ISR, migration: DataMigrationIntent, *, module_id: str
    ) -> MutationCandidate:
        """Declare one migration intent — nothing else changes."""
        module = next(m for m in isr.system.modules if m.id == module_id)
        existing = {m.migration_id for m in module.data_migrations}
        if migration.migration_id in existing:
            raise MigrationValidationError(
                f"migration '{migration.migration_id}' already declared in "
                f"module '{module_id}'"
            )
        after = self._replace_module_migrations(
            isr, module_id, module.data_migrations + (migration,)
        )
        self._attest(isr, after, "add_migration", migration)
        return self._candidate(isr, after, "add_migration", migration)

    def remove_migration(
        self, isr: ISR, *, migration_id: str, module_id: str
    ) -> MutationCandidate:
        """Remove one migration intent — the referenced data genes are untouched."""
        module = next(m for m in isr.system.modules if m.id == module_id)
        for migration in module.data_migrations:
            if migration.migration_id == migration_id:
                after = self._replace_module_migrations(
                    isr,
                    module_id,
                    tuple(
                        m
                        for m in module.data_migrations
                        if m.migration_id != migration_id
                    ),
                )
                self._attest(isr, after, "remove_migration", migration)
                return self._candidate(isr, after, "remove_migration", migration)
        raise MigrationValidationError(
            f"migration '{migration_id}' not found in module '{module_id}'"
        )

    def set_compatibility_policy(
        self,
        isr: ISR,
        *,
        migration_id: str,
        policy: CompatibilityPolicy,
        module_id: str,
    ) -> MutationCandidate:
        """Respecify compatibility INTENT; every other dimension is untouched."""
        module = next(m for m in isr.system.modules if m.id == module_id)
        for migration in module.data_migrations:
            if migration.migration_id == migration_id:
                edited = dataclasses.replace(
                    migration, compatibility_policy=policy
                )
                after = self._replace_module_migrations(
                    isr,
                    module_id,
                    tuple(
                        edited if m.migration_id == migration_id else m
                        for m in module.data_migrations
                    ),
                )
                self._attest(isr, after, "set_compatibility_policy", edited)
                return self._candidate(isr, after, "set_compatibility_policy", edited)
        raise MigrationValidationError(
            f"migration '{migration_id}' not found in module '{module_id}'"
        )

    def add_preservation_ref(
        self, isr: ISR, *, migration_id: str, entity_ref: str, module_id: str
    ) -> MutationCandidate:
        """Add one data gene to the preservation requirement (identity only)."""
        module = next(m for m in isr.system.modules if m.id == module_id)
        for migration in module.data_migrations:
            if migration.migration_id == migration_id:
                if entity_ref in migration.preservation_refs:
                    raise MigrationValidationError(
                        f"entity '{entity_ref}' already preserved by "
                        f"'{migration_id}'"
                    )
                edited = dataclasses.replace(
                    migration,
                    preservation_refs=migration.preservation_refs + (entity_ref,),
                )
                after = self._replace_module_migrations(
                    isr,
                    module_id,
                    tuple(
                        edited if m.migration_id == migration_id else m
                        for m in module.data_migrations
                    ),
                )
                self._attest(isr, after, "add_preservation_ref", edited)
                return self._candidate(isr, after, "add_preservation_ref", edited)
        raise MigrationValidationError(
            f"migration '{migration_id}' not found in module '{module_id}'"
        )

    # -- deterministic generation ---------------------------------------------------

    def generate(
        self,
        isr: ISR,
        *,
        seed: Optional[int] = None,
        population_size: int = 1,
    ) -> tuple[MutationCandidate, ...]:
        """Seed-replayable candidate generation over the migration gene class.

        Deterministic by construction: candidates migrate consecutive sorted
        entity pairs (e0 -> e1, e1 -> e2, ...) and carry no randomness —
        ``seed`` is accepted for protocol compatibility and reproducibility
        attestation.
        """
        del seed
        candidates: list[MutationCandidate] = []
        for module in sorted(isr.system.modules, key=lambda m: m.id):
            entities = sorted(e.id for e in module.entities)
            for i in range(min(len(entities) - 1, population_size)):
                migration = DataMigrationIntent(
                    migration_id=f"mig.{entities[i]}.to.{entities[i + 1]}",
                    source_schema_ref=entities[i],
                    target_schema_ref=entities[i + 1],
                    compatibility_policy=CompatibilityPolicy.BACKWARD,
                    preservation_refs=(entities[i],),
                    rollback_required=True,
                    rollback_target_ref=entities[i],
                    rollback_invariants=(f"{entities[i]} intact",),
                    postconditions=(f"{entities[i + 1]} valid",),
                )
                candidates.append(
                    self.add_migration(isr, migration, module_id=module.id)
                )
        return tuple(candidates)