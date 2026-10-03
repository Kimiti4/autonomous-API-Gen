from app.engine.fullstack_architecture_ir import *

def source():
    return FullStackArchitectureIR(
        "A1",
        (
            ArchitectureComponent("ui","frontend",("presentation",)),
            ArchitectureComponent("api","backend",("business logic",)),
            ArchitectureComponent("db","persistence",("authority",)),
        ),
        ("GET /vehicles","POST /swaps"),
        ("swap-idempotent",),
    )

def test_frontend_and_backend_are_projections_not_sources():
    s=source()
    f=project_frontend(s); b=project_backend(s)
    assert [x.component_id for x in f.components]==["ui"]
    assert [x.component_id for x in b.components]==["api","db"]

def test_projections_preserve_contracts_and_invariants():
    s=source()
    assert assert_projection_consistency(s,project_frontend(s),project_backend(s))

def test_wrong_architecture_identity_is_rejected():
    s=source()
    f=FrontendArchitectureIR("OTHER",(),(),())
    assert not assert_projection_consistency(s,f,project_backend(s))
