from isr.core.graph import ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from compiler.backends.android import AndroidStructuralBackend, compile_isr_revision
from compiler.core.plan import CompilationPlan, DataModel, Service, ApiOperation, FrontendRoute
from compiler.core.protocol import BackendClass, CompilerBackend


def static_plan(**updates):
    values = dict(
        plan_id="plan:test",
        isr_id="inventory",
        data_models=[DataModel(id="dm:item", entity_name="Item")],
    )
    values.update(updates)
    return CompilationPlan(**values)


def test_android_backend_implements_campaign_protocol_and_is_structural():
    backend = AndroidStructuralBackend()
    assert isinstance(backend, CompilerBackend)
    assert backend.identity().backend_class is BackendClass.STRUCTURAL
    assert backend.test_spec().command == ["gradle", ":app:assembleDebug", "--no-daemon"]


def test_android_backend_emits_deterministic_candidate_and_conforms():
    backend = AndroidStructuralBackend()
    plan = static_plan()
    first = backend.compile(plan)
    second = backend.compile(plan)
    assert first.content_hash == second.content_hash
    assert backend.conformance(plan, first).passed
    assert "StaticCatalogue" in first.files["app/src/main/java/generated/app/MainActivity.kt"]


def test_android_backend_refuses_unimplemented_semantics_before_emission():
    backend = AndroidStructuralBackend()
    unsupported = (
        static_plan(services=[Service(id="svc:catalogue", name="Catalogue")]),
        static_plan(apis=[ApiOperation(id="api:items", name="Items")]),
        static_plan(frontend_routes=[FrontendRoute(id="route:items", name="Items")]),
    )
    for plan in unsupported:
        try:
            backend.compile(plan)
        except ValueError:
            pass
        else:
            raise AssertionError("unsupported semantics were accepted")


def test_isr_revision_entrypoint_binds_revision_plan_and_candidate():
    graph = ISRGraph(nodes={
        "dm:item": Node(
            id="dm:item", type=NodeType.DATA_MODEL,
            properties={"label": "Item"},
        )
    })
    revision = ISRRevision.create(
        system_id="inventory", revision_id="rev:item", schema_version="1.0",
        graph=graph,
        provenance=Provenance(
            created_by="test", created_at="2026-11-03T00:00:00Z",
            requirement_refs=["req:item"], derivation_refs=["test-fixture"],
        ),
    )
    candidate = compile_isr_revision(revision)
    assert candidate.revision_hash == revision.content_hash
    assert len(candidate.plan_hash) == 64
    assert candidate.repository.content_hash
    assert "Item" in candidate.repository.files[
        "app/src/main/java/generated/app/MainActivity.kt"
    ]
