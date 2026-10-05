from app.engine.implementation_traceability import derive_implementation_trace
from app.engine.architecture_obligations import ArchitectureObligation, ObligationMapping
from app.engine.implementation_ir import FrontendIR, ModuleIR

def test_trace_reaches_implementation_and_verification():
    o=ArchitectureObligation("AO-1","R-1","invariant","must hold",("verify-1",))
    m=ObligationMapping("AO-1",("auth",),True,"mapped",("verify-1",))
    ir=FrontendIR("1","c",("/login",),"api",modules=(ModuleIR("auth","authentication"),))
    p=derive_implementation_trace((o,),(m,),frontend=ir)
    assert p.complete
    assert p.traces[0].implementation_ids==("impl:auth",)
    assert p.traces[0].verification_ids==("verify-1",)

def test_missing_component_remains_unresolved():
    o=ArchitectureObligation("AO-1","R-1","policy","authorize",("verify-1",))
    m=ObligationMapping("AO-1",("missing",),True,"mapped",("verify-1",))
    p=derive_implementation_trace((o,),(m,),frontend=FrontendIR("1","c",(),"api"))
    assert p.unresolved_obligations==("AO-1",)
