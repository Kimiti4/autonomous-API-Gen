"""Production workflow stage audit (Checkpoint 054)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowDisposition(str, Enum):
    IMPLEMENTED = "implemented"
    REGISTERED = "registered"
    INVOKED = "invoked"
    EXECUTED = "executed"
    VERIFIED = "verified"
    DISCONNECTED = "disconnected"


@dataclass(frozen=True)
class WorkflowStage:
    stage_id: str
    description: str
    entrypoint: str
    disposition: WorkflowDisposition
    notes: str = ""


def production_workflow_stages() -> tuple[WorkflowStage, ...]:
    """Honest map of the compiler path used for ordinary workloads (not payroll/orders fixtures)."""
    return (
        WorkflowStage(
            "01_requirement_intake",
            "TOR text normalized to requirement candidates",
            "reqgraph.ingestion.tor_extractor.extract_tor_text",
            WorkflowDisposition.VERIFIED,
        ),
        WorkflowStage(
            "02_requirement_approval",
            "Human approval metadata bound to requirement graph",
            "RequirementGraph.approve",
            WorkflowDisposition.INVOKED,
            "Ordinary workloads use explicit HumanApproval in workload modules",
        ),
        WorkflowStage(
            "03_isr_architecture",
            "Domain ISR graph authored from workload spec",
            "certification.ordinary.workloads.*.isr_revision",
            WorkflowDisposition.INVOKED,
            "Architecture nodes are workload-specific; not payroll/orders proving fixtures",
        ),
        WorkflowStage(
            "04_requirement_projection",
            "Approved requirements merged into ISR",
            "reqgraph.adapters.isr_projection.merge_requirement_projection",
            WorkflowDisposition.VERIFIED,
        ),
        WorkflowStage(
            "05_isr_to_plan",
            "ISR lowered to compilation plan",
            "compiler.core.lowering.isr_to_plan",
            WorkflowDisposition.VERIFIED,
        ),
        WorkflowStage(
            "06_canonical_contract",
            "Shared API contract derived from plan",
            "compiler.core.canonical_api_contract.build_canonical_api_contract",
            WorkflowDisposition.VERIFIED,
        ),
        WorkflowStage(
            "07_frontend_compile",
            "React frontend generation",
            "compiler.backends.react_frontend.ReactFrontendBackend.compile",
            WorkflowDisposition.EXECUTED,
        ),
        WorkflowStage(
            "08_backend_compile",
            "Python FastAPI backend generation",
            "compiler.backends.python_fastapi.PythonFastAPIBackend.compile",
            WorkflowDisposition.EXECUTED,
        ),
        WorkflowStage(
            "09_full_stack_verify",
            "Structural/behavioral coherence",
            "certification.proving.plan_full_stack_bridge.verify_plan_full_stack",
            WorkflowDisposition.INVOKED,
        ),
        WorkflowStage(
            "10_runtime_execution",
            "pytest/cargo on generated tree",
            "tests/execution/* (opt-in subprocess)",
            WorkflowDisposition.DISCONNECTED,
            "Not wired as default post-compile hook for ordinary workloads",
        ),
        WorkflowStage(
            "11_trusted_evidence",
            "CP052 staging and conformance records",
            "certification.product.governed_lifecycle.run_governed_product_lifecycle",
            WorkflowDisposition.INVOKED,
            "Payroll/orders lifecycle orchestrator; ordinary uses certification.ordinary.orchestration",
        ),
        WorkflowStage(
            "12_product_factory",
            "Phase 18 market/product factory",
            "product_factory.engine",
            WorkflowDisposition.DISCONNECTED,
            "Parallel product line; not the compiler path exercised here",
        ),
        WorkflowStage(
            "13_autonomous_api_intent",
            "Intent compiler LLM port",
            "tiannara.application.intent.compiler",
            WorkflowDisposition.DISCONNECTED,
            "Not on critical path for deterministic compiler proofs",
        ),
    )
