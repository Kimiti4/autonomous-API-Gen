from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.application.compiler.selector import plan_compilation_across_backends
from tiannara.application.hardening.fullstack_gates import (
    FULLSTACK_HARDENING_GATES,
    GateResult,
    GateStatus,
    certify_hardening,
)
from tiannara.domain.models.backend_declaration import CompilationRequirement


def test_compiler_matrix_resolves_every_registered_backend():
    registry = build_compiler_registry()
    declarations = list(registry.declarations())
    assert len(declarations) >= 20

    requirements = [
        CompilationRequirement(
            artifact_kind=kind,
            required_capabilities=list(declaration.capabilities),
            subject_ref=f"matrix:{declaration.backend_id}",
        )
        for declaration in declarations
        for kind in declaration.artifact_kinds
    ]
    plan = plan_compilation_across_backends(registry, requirements)

    planned_backend_ids = {item.backend_id for item in plan.planned}
    declared_backend_ids = {item.backend_id for item in declarations}
    assert declared_backend_ids <= planned_backend_ids


def test_compiler_matrix_is_deterministic():
    registry = build_compiler_registry()
    declarations = list(registry.declarations())
    requirements = [
        CompilationRequirement(
            artifact_kind=declaration.artifact_kinds[0],
            required_capabilities=list(declaration.capabilities),
            subject_ref=f"matrix:{declaration.backend_id}",
        )
        for declaration in declarations
    ]
    first = plan_compilation_across_backends(registry, requirements)
    second = plan_compilation_across_backends(registry, requirements)
    assert first.plan_id == second.plan_id
    assert [x.backend_id for x in first.planned] == [x.backend_id for x in second.planned]


def test_matrix_candidate_cannot_be_certified_without_runtime_evidence():
    passing_but_incomplete = [
        GateResult(g.gate_id, GateStatus.PASS)
        for g in FULLSTACK_HARDENING_GATES[:-2]
    ]
    assert not certify_hardening(passing_but_incomplete)
