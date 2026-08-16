"""R2.10.3-C — data migrations primitive (semantic intent, never mechanism).

The ISR declares data-evolution intent and invariants; compiler backends
later decide how that intent is physically realized. This is the primitive
where the semantic layer is most likely to accidentally become a database
compiler, so the construct is STRUCTURALLY incapable of carrying an
execution mechanism: no SQL, no ORM models, no database-engine references,
no framework commands, no runnable script. Rollback is expressed as
invariants-to-preserve, never as a command to run.

Semantics modeled (foundations for R2.10.3-D reliability_resilience and
R2.10.3-E architecture_boundaries):
  * compatibility INTENT (declared goal; validation is a future stage)
  * preservation requirements (reference-based, implementation-independent)
  * ordering (an explicit acyclic dependency graph among migrations)
  * rollback semantics (what rollback must accomplish, not how)
  * validation postconditions (future evaluation inputs)

Schema references resolve to ``Module.entities`` (the data-model genes); a
dedicated schema construct is a follow-up if granularity beyond entities is
ever needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Optional

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class MigrationValidationError(ValueError):
    """A migration intent violates its construction or structural contract."""


@unique
class CompatibilityPolicy(str, Enum):
    """Compatibility INTENT. Declares the goal; validation determines whether
    a proposed evolution satisfies it. The enum is never itself the policy."""

    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    BREAKING = "BREAKING"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class DataMigrationIntent:
    """Semantic data-evolution intent: WHAT a migration must accomplish, never HOW.

    Declares compatibility intent, preservation requirements, ordering, rollback
    semantics, and validation postconditions. Contains NO SQL, NO ORM models, NO
    database-engine references, NO framework commands, and NO executable mechanism.

    Rollback is expressed as invariants-to-preserve, never as a command to run.
    This is the boundary that keeps the primitive from becoming a database compiler.
    """

    migration_id: str
    source_schema_ref: str
    target_schema_ref: str
    compatibility_policy: CompatibilityPolicy
    preservation_refs: tuple[str, ...] = ()  # data genes that must survive
    depends_on: tuple[str, ...] = ()  # migration_ids this depends on
    rollback_required: bool = False
    rollback_target_ref: Optional[str] = None
    rollback_invariants: tuple[str, ...] = ()  # what rollback must preserve
    postconditions: tuple[str, ...] = ()  # validation requirements

    def __post_init__(self) -> None:
        if not self.migration_id:
            raise MigrationValidationError("migration_id is required")
        if not self.source_schema_ref:
            raise MigrationValidationError("source_schema_ref is required")
        if not self.target_schema_ref:
            raise MigrationValidationError("target_schema_ref is required")
        if self.source_schema_ref == self.target_schema_ref:
            raise MigrationValidationError("source and target schemas must differ")
        if self.rollback_required and not self.rollback_target_ref:
            raise MigrationValidationError(
                "rollback_required demands a rollback_target_ref"
            )
        if (
            self.compatibility_policy is CompatibilityPolicy.CUSTOM
            and not self.postconditions
        ):
            raise MigrationValidationError(
                "CUSTOM compatibility requires declared postconditions"
            )


# -- mechanism lint (the dangerous boundary) ---------------------------------

MIGRATION_MECHANISM_TERMS: frozenset[str] = frozenset({
    "alembic", "ecto", "prisma", "flyway", "liquibase",
    "migration_script", "migration_command", "rollback_command",
    "orm_model", "ddl", "dml",
})


def migration_mechanism_hits(migration: DataMigrationIntent) -> tuple[str, ...]:
    """Which mechanism terms (if any) leaked into a migration's semantic form."""
    lowered = canonicalize(migration).lower()
    return tuple(term for term in MIGRATION_MECHANISM_TERMS if term in lowered)


def assert_migration_technology_agnostic(migration: DataMigrationIntent) -> None:
    """Gate: no implementation mechanism may leak into the semantic representation."""
    hits = migration_mechanism_hits(migration)
    if hits:
        raise MigrationValidationError(
            f"migration '{migration.migration_id}' couples to mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _module_entity_ids(module: Any) -> set[str]:
    return {entity.id for entity in module.entities}


def _validate_acyclic(
    module: Any, by_id: dict[str, DataMigrationIntent]
) -> list[str]:
    """Walk the depends_on graph; a cycle makes ordering meaningless."""
    errors: list[str] = []
    state: dict[str, int] = {}  # 0 = unvisited, 1 = visiting, 2 = done

    def visit(migration_id: str, stack: tuple[str, ...]) -> None:
        status = state.get(migration_id, 0)
        if status == 2:
            return
        if status == 1:
            cycle = " -> ".join(stack + (migration_id,))
            errors.append(f"circular migration dependency: {cycle}")
            return
        state[migration_id] = 1
        for dep in by_id[migration_id].depends_on:
            if dep not in by_id:
                continue  # dangling dependency — already reported by the caller
            visit(dep, stack + (migration_id,))
        state[migration_id] = 2

    for migration_id in by_id:
        visit(migration_id, ())
    return errors


def validate_module_migration_constraints(module: Any) -> tuple[str, ...]:
    """Structural validation for one module's migration intents.

    Rejects, pre-execution: duplicate migration ids, dangling source/target
    schema refs (must name entities of this module), dangling preservation
    refs, dangling depends_on refs, and circular depends_on graphs.
    Empty tuple means valid.
    """
    errors: list[str] = []
    entity_ids = _module_entity_ids(module)
    all_ids = {m.migration_id for m in module.data_migrations}
    by_id: dict[str, DataMigrationIntent] = {}
    for migration in module.data_migrations:
        if migration.migration_id in by_id:
            errors.append(
                f"duplicate migration id '{migration.migration_id}' in module "
                f"'{module.id}'"
            )
        by_id[migration.migration_id] = migration
        if migration.source_schema_ref not in entity_ids:
            errors.append(
                f"migration '{migration.migration_id}' references unknown source "
                f"schema '{migration.source_schema_ref}' in module '{module.id}'"
            )
        if migration.target_schema_ref not in entity_ids:
            errors.append(
                f"migration '{migration.migration_id}' references unknown target "
                f"schema '{migration.target_schema_ref}' in module '{module.id}'"
            )
        if migration.rollback_target_ref not in (None, migration.source_schema_ref):
            errors.append(
                f"migration '{migration.migration_id}' rollback target "
                f"'{migration.rollback_target_ref}' is not its source schema "
                f"'{migration.source_schema_ref}'"
            )
        for preservation_ref in migration.preservation_refs:
            if preservation_ref not in entity_ids:
                errors.append(
                    f"migration '{migration.migration_id}' preserves unknown data "
                    f"gene '{preservation_ref}' in module '{module.id}'"
                )
        for dependency in migration.depends_on:
            if dependency not in all_ids:
                errors.append(
                    f"migration '{migration.migration_id}' depends on unknown "
                    f"migration '{dependency}' in module '{module.id}'"
                )
    errors.extend(_validate_acyclic(module, by_id))
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_data_migrations(module: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of migration intents.

    Returns migration semantics (compatibility intent, preservation, ordering,
    rollback invariants, postconditions). Never SQL, ORM models, or runnable
    scripts — those are compiler-backend realizations, not the migration.
    """
    return tuple(
        canonical_form(migration) for migration in getattr(module, "data_migrations", ())
    )