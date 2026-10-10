from tiannara.application.certification.production_readiness import (
    BlockingDimension,
    ProductionReadinessGate,
    ProductionReadinessResult,
    ProductionReadinessVerdict,
)
from tiannara.application.hardening.fullstack_gates import (
    FULLSTACK_HARDENING_GATES,
    GateResult,
    GateStatus,
)


def _ready_result():
    return ProductionReadinessResult(
        ProductionReadinessVerdict.PRODUCTION_READY,
        (),
        (),
        "readiness-ref",
    )


class StubGate(ProductionReadinessGate):
    def evaluate(self, evidence):
        return _ready_result()


def test_production_readiness_blocks_when_hardening_is_incomplete():
    gate = StubGate.__new__(StubGate)
    result = gate.evaluate_generated_application(
        {},
        compilation_ok=True,
        hardening_results=(
            GateResult("BACKEND-BUILD", GateStatus.PASS),
        ),
    )
    assert result.verdict is ProductionReadinessVerdict.NOT_PRODUCTION_READY
    assert any(b.dimension == "fullstack-hardening" for b in result.blocking_dimensions)


def test_production_readiness_accepts_complete_hardening_contract():
    gate = StubGate.__new__(StubGate)
    results = tuple(
        GateResult(g.gate_id, GateStatus.PASS, (f"evidence:{g.gate_id}",))
        for g in FULLSTACK_HARDENING_GATES
    )
    result = gate.evaluate_generated_application(
        {},
        compilation_ok=True,
        hardening_results=results,
    )
    assert result.verdict is ProductionReadinessVerdict.PRODUCTION_READY
    assert result.blocking_dimensions == ()
