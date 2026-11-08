"""Repository-wide orchestration entry-point inventory (Checkpoint 055)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IngressEnforcement(str, Enum):
    REACHABLE_ENFORCED = "reachable_enforced"
    REACHABLE_SUBORDINATE = "reachable_subordinate"
    REACHABLE_BLOCKED = "reachable_blocked"
    DEVELOPMENT_ONLY = "development_only"
    UNMOUNTED = "unmounted"
    DISCONNECTED = "disconnected"
    UNVERIFIED = "unverified"


class EntryDisposition(str, Enum):
    CANONICAL_AUTHORITY = "canonical_authority"
    SUBORDINATE_COMPILER = "subordinate_compiler"
    DELEGATED_SPECIALIST = "delegated_specialist"
    DEVELOPMENT_ONLY = "development_only"
    DISCONNECTED = "disconnected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class OrchestrationEntryPoint:
    entry_id: str
    module_path: str
    production_reachable: bool
    is_independent_authority: bool
    disposition: EntryDisposition
    invokes_stages: tuple[str, ...]
    skips_mandatory: tuple[str, ...]
    can_publish_alone: bool
    conflicts_with_canonical: bool
    enforcement: IngressEnforcement = IngressEnforcement.UNVERIFIED
    notes: str = ""


def orchestration_entry_inventory() -> tuple[OrchestrationEntryPoint, ...]:
    return (
        OrchestrationEntryPoint(
            "canonical_full_stack",
            "certification.orchestration.authority.FullStackOrchestrationAuthority.run",
            production_reachable=True,
            is_independent_authority=True,
            disposition=EntryDisposition.CANONICAL_AUTHORITY,
            invokes_stages=(
                "requirements",
                "isr",
                "plan",
                "compile",
                "integration_verify",
                "senior",
                "evidence",
                "governance_stage",
            ),
            skips_mandatory=(),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            notes="Mandatory path for governed full-stack product requests",
        ),
        OrchestrationEntryPoint(
            "http_full_stack_run",
            "autonomous-api POST /api/v1/orchestration/full-stack/run",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.CANONICAL_AUTHORITY,
            invokes_stages=(
                "requirements",
                "isr",
                "plan",
                "compile",
                "integration_verify",
                "senior",
                "evidence",
                "governance_stage",
            ),
            skips_mandatory=(),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            enforcement=IngressEnforcement.REACHABLE_ENFORCED,
            notes="CP056 production HTTP ingress; delegates to FullStackOrchestrationAuthority",
        ),
        OrchestrationEntryPoint(
            "http_dashboard_full_stack_run",
            "autonomous-api POST /api/v1/dashboard/orchestration/full-stack/run",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.CANONICAL_AUTHORITY,
            invokes_stages=(
                "requirements",
                "isr",
                "plan",
                "compile",
                "integration_verify",
                "senior",
                "evidence",
                "governance_stage",
            ),
            skips_mandatory=(),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            enforcement=IngressEnforcement.REACHABLE_ENFORCED,
            notes="CP057 dashboard session/API ingress",
        ),
        OrchestrationEntryPoint(
            "http_evolve",
            "autonomous-api POST /api/v1/evolve/*",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.SUBORDINATE_COMPILER,
            invokes_stages=("compile",),
            skips_mandatory=("senior", "evidence", "governance"),
            can_publish_alone=False,
            conflicts_with_canonical=True,
            enforcement=IngressEnforcement.REACHABLE_SUBORDINATE,
            notes="CP057: 403 on claim_governed_product_lifecycle; promotion blocked when governed production",
        ),
        OrchestrationEntryPoint(
            "cli_full_stack_run",
            "tiannara full-stack run",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.CANONICAL_AUTHORITY,
            invokes_stages=(
                "requirements",
                "isr",
                "plan",
                "compile",
                "integration_verify",
                "senior",
                "evidence",
                "governance_stage",
            ),
            skips_mandatory=(),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            enforcement=IngressEnforcement.REACHABLE_ENFORCED,
            notes="CP056 governed CLI ingress",
        ),
        OrchestrationEntryPoint(
            "cli_factory_create",
            "tiannara create|factory",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.DEVELOPMENT_ONLY,
            invokes_stages=("compile",),
            skips_mandatory=("governance",),
            can_publish_alone=False,
            conflicts_with_canonical=True,
            enforcement=IngressEnforcement.REACHABLE_SUBORDINATE,
            notes="CP057: exit 2 under ESAP_GOVERNED_PRODUCTION unless --dev-subordinate",
        ),
        OrchestrationEntryPoint(
            "compiler_lowering",
            "compiler.core.lowering.isr_to_plan",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.SUBORDINATE_COMPILER,
            invokes_stages=("plan",),
            skips_mandatory=("senior", "evidence", "governance"),
            can_publish_alone=False,
            conflicts_with_canonical=False,
        ),
        OrchestrationEntryPoint(
            "backend_compile_python",
            "compiler.backends.python_fastapi.PythonFastAPIBackend.compile",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.SUBORDINATE_COMPILER,
            invokes_stages=("compile",),
            skips_mandatory=("requirements", "senior", "evidence"),
            can_publish_alone=False,
            conflicts_with_canonical=True,
            notes="Must not claim lifecycle completion without authority",
        ),
        OrchestrationEntryPoint(
            "product_governed_lifecycle",
            "certification.product.governed_lifecycle.run_governed_product_lifecycle",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.SUPERSEDED,
            invokes_stages=("compile", "evidence", "senior"),
            skips_mandatory=("requirements_explicit"),
            can_publish_alone=False,
            conflicts_with_canonical=True,
            notes="Delegates to canonical authority in CP055",
        ),
        OrchestrationEntryPoint(
            "ordinary_orchestration",
            "certification.ordinary.orchestration.run_ordinary_workload",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.SUPERSEDED,
            invokes_stages=("compile", "verify", "evidence"),
            skips_mandatory=(),
            can_publish_alone=False,
            conflicts_with_canonical=True,
            notes="Delegates to canonical authority in CP055",
        ),
        OrchestrationEntryPoint(
            "payroll_proving_case",
            "certification.payroll.proving_case.run_payroll_proving_case",
            production_reachable=False,
            is_independent_authority=False,
            disposition=EntryDisposition.DELEGATED_SPECIALIST,
            invokes_stages=("compile", "readiness", "oracle"),
            skips_mandatory=("canonical_orchestration_contract",),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            notes="Certification/reporting; routes through authority when governance paths set",
        ),
        OrchestrationEntryPoint(
            "orders_proving_case",
            "certification.orders.proving_case.run_orders_proving_case",
            production_reachable=False,
            is_independent_authority=False,
            disposition=EntryDisposition.DELEGATED_SPECIALIST,
            invokes_stages=("compile", "verify"),
            skips_mandatory=("canonical_orchestration_contract",),
            can_publish_alone=False,
            conflicts_with_canonical=False,
        ),
        OrchestrationEntryPoint(
            "governed_promotion",
            "constitutional_architecture.governance.candidate_promotion_lifecycle.GovernedCandidatePromotionService",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.DELEGATED_SPECIALIST,
            invokes_stages=("governance_stage", "certify", "promote"),
            skips_mandatory=("compile",),
            can_publish_alone=False,
            conflicts_with_canonical=False,
        ),
        OrchestrationEntryPoint(
            "autonomous_api_publication",
            "autonomous-api/app/engine/governed_publication_gateway.py",
            production_reachable=True,
            is_independent_authority=False,
            disposition=EntryDisposition.DELEGATED_SPECIALIST,
            invokes_stages=("publication",),
            skips_mandatory=("compile", "senior"),
            can_publish_alone=False,
            conflicts_with_canonical=False,
            notes="Publication requires pre-staged candidate from authority",
        ),
        OrchestrationEntryPoint(
            "product_factory",
            "product_factory.engine",
            production_reachable=False,
            is_independent_authority=True,
            disposition=EntryDisposition.DISCONNECTED,
            invokes_stages=("market",),
            skips_mandatory=("isr", "compiler", "evidence"),
            can_publish_alone=True,
            conflicts_with_canonical=True,
        ),
        OrchestrationEntryPoint(
            "intent_compiler",
            "tiannara.application.intent.compiler",
            production_reachable=False,
            is_independent_authority=True,
            disposition=EntryDisposition.DISCONNECTED,
            invokes_stages=("intent",),
            skips_mandatory=("trusted_evidence",),
            can_publish_alone=False,
            conflicts_with_canonical=True,
        ),
        OrchestrationEntryPoint(
            "software_factory",
            "tiannara.application.factory.factory.SoftwareFactory",
            production_reachable=False,
            is_independent_authority=True,
            disposition=EntryDisposition.DISCONNECTED,
            invokes_stages=("evolution_feedback",),
            skips_mandatory=("full_stack",),
            can_publish_alone=False,
            conflicts_with_canonical=True,
        ),
    )
