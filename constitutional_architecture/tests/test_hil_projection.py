"""
Phase 16.1 — HIL Projection Engine property tests.

Properties under test (ratified in ESAP-HIL-ARCH-001):
  P1  deterministic projection   — identical inputs yield identical
      UIPM output regardless of grant/tree input order
  P2  deny-by-default            — no grant => no surface; every denial
      carries an explainable reason `requires <cap>`
  P3  additive migration         — deprecate(old)+introduce(new) emits
      BOTH claims during the compatibility window, then cuts over
  P4  renderer equivalence       — capability + command surfaces are
      identical across renderer backends; layout differs
  P5  latency budgets            — nav <= 16ms, layout <= 100ms
  P6  projection_ref             — pure, re-derivable, sensitive to every
      input (isr_snapshot, principal, capability_schema_ver, uipm_ver)
"""

import json

from constitutional_architecture.core.hil import (
    Capability,
    CapabilityRegistry,
    NavigationEntry,
    PolicyEngine,
    ProjectionRequest,
    UIPMSerializer,
    projection_ref,
)


def make_registry() -> CapabilityRegistry:
    reg = CapabilityRegistry()
    for cap_id, name, family in [
        ("dash.overview", "Overview", "dash"),
        ("isr.explore", "ISR explorer", "isr"),
        ("isr.history", "ISR history", "isr"),
        ("lab.candidates", "Evolution lab", "lab"),
        ("lab.mutate", "Targeted mutation", "lab"),
        ("deploy.promote", "Promotion", "deploy"),
        ("obs.telemetry", "Telemetry", "obs"),
        ("obs.log", "Log stream", "obs"),
        ("ops.run", "Run generation", "ops"),
        ("ops.arbitration", "Arbitration records", "ops"),
        ("ops.dismiss", "Dismiss", "ops"),
    ]:
        reg.register(Capability(id=cap_id, name=name, family=family))
    return reg


def make_nav_tree() -> list[NavigationEntry]:
    return [
        NavigationEntry(
            id="dash", label="Dashboard", capability="dash.overview",
            children=[
                NavigationEntry(
                    id="isr", label="ISR", capability="isr.explore",
                    children=[
                        NavigationEntry(id="isr.hist", label="History",
                                        capability="isr.history"),
                    ],
                ),
            ],
        ),
        NavigationEntry(
            id="lab", label="Evolution Lab", capability="lab.candidates",
            children=[
                NavigationEntry(id="lab.mut", label="Mutate",
                                capability="lab.mutate"),
            ],
        ),
        NavigationEntry(id="deploy", label="Deployment",
                        capability="deploy.promote"),
    ]


def make_request(**overrides) -> ProjectionRequest:
    params = dict(
        isr_snapshot_id="snap-9f3c",
        principal="operator",
        capability_schema_ver="governance.1",
    )
    params.update(overrides)
    return ProjectionRequest(**params)


class TestProjectionRef:
    """P6 — projection_ref is a pure, re-derivable content address."""

    def test_same_request_same_ref(self):
        assert projection_ref(make_request()) == projection_ref(make_request())

    def test_ref_sensitive_to_snapshot(self):
        a = projection_ref(make_request(isr_snapshot_id="snap-a"))
        b = projection_ref(make_request(isr_snapshot_id="snap-b"))
        assert a != b

    def test_ref_sensitive_to_principal(self):
        a = projection_ref(make_request(principal="operator"))
        b = projection_ref(make_request(principal="auditor"))
        assert a != b

    def test_ref_sensitive_to_schema_version(self):
        a = projection_ref(make_request(capability_schema_ver="governance.1"))
        b = projection_ref(make_request(capability_schema_ver="governance.2"))
        assert a != b

    def test_ref_sensitive_to_uipm_version(self):
        a = projection_ref(make_request(uipm_ver="1.0"))
        b = projection_ref(make_request(uipm_ver="1.1"))
        assert a != b

    def test_document_carries_derived_ref(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        doc = serializer.serialize(
            make_request(),
            granted=["dash.overview", "isr.explore"],
            nav_tree=make_nav_tree(),
        )
        assert doc.projection_ref == projection_ref(make_request())


class TestDenyByDefault:
    """P2 — nothing is shown without a claim; denials are explainable."""

    def test_no_grants_yields_empty_projection_with_denials(self):
        reg = make_registry()
        engine = PolicyEngine(reg)
        proj = engine.project_navigation("auditor", [], make_nav_tree())
        assert proj.entries == []
        assert len(proj.denials) == len(make_nav_tree())
        for d in proj.denials:
            assert d.reason == f"requires {d.capability}"

    def test_unknown_grants_are_ignored(self):
        reg = make_registry()
        engine = PolicyEngine(reg)
        proj = engine.project_navigation(
            "operator", ["nonsense.cap", "not-registered"], make_nav_tree()
        )
        assert proj.entries == []

    def test_full_grants_show_everything_without_denials(self):
        reg = make_registry()
        engine = PolicyEngine(reg)
        all_caps = reg.valid_ids()
        proj = engine.project_navigation("operator", all_caps, make_nav_tree())
        assert len(proj.denials) == 0
        assert set(proj.visible_ids()) == {"dash", "isr", "isr.hist", "lab",
                                           "lab.mut", "deploy"}

    def test_unknown_required_capability_is_denied(self):
        reg = make_registry()
        engine = PolicyEngine(reg)
        decision = engine.authorize("operator", "ghost.cap")
        assert not decision.allowed
        assert decision.denial is not None
        assert "ghost.cap" in decision.denial.reason

    def test_retired_capability_emits_no_claims(self):
        reg = make_registry()
        reg.retire("obs.telemetry")
        assert "obs.telemetry" not in reg.claims_for({"obs.telemetry"})
        assert "obs.telemetry" not in reg.valid_ids()


class TestAdditiveMigration:
    """P3 — deprecate(old)+introduce(new), both claims during the window."""

    def test_both_claims_emitted_during_compatibility_window(self):
        reg = make_registry()
        reg.introduce(
            "lab.curate", "Curate candidates", "lab", replaces="lab.mutate"
        )
        claims_old_holder = reg.claims_for({"lab.mutate"})
        assert "lab.mutate" in claims_old_holder
        assert "lab.curate" in claims_old_holder
        claims_new_holder = reg.claims_for({"lab.curate"})
        assert "lab.curate" in claims_new_holder

    def test_after_window_only_new_emits(self):
        reg = make_registry()
        reg.introduce(
            "lab.curate", "Curate candidates", "lab", replaces="lab.mutate"
        )
        for _ in range(reg.compatibility_window):
            reg.advance_schema_version()
        assert reg.claims_for({"lab.mutate"}) == frozenset()
        assert reg.claims_for({"lab.curate"}) == frozenset({"lab.curate"})

    def test_migration_is_never_in_place(self):
        reg = make_registry()
        old = reg.get("lab.mutate")
        reg.introduce(
            "lab.curate", "Curate candidates", "lab", replaces="lab.mutate"
        )
        assert old.id == "lab.mutate"
        assert reg.get("lab.mutate").status.value == "deprecated"
        assert reg.get("lab.curate").replaces == "lab.mutate"

    def test_alias_resolves_to_target(self):
        reg = make_registry()
        reg.add_alias("lab.run", "lab.candidates")
        assert reg.claims_for({"lab.run"}) == frozenset({"lab.candidates"})

    def test_ledger_hash_is_deterministic_and_content_addressed(self):
        a, b = make_registry(), make_registry()
        assert a.ledger_hash() == b.ledger_hash()
        a.introduce("x.new", "New", "lab", replaces="lab.mutate")
        assert a.ledger_hash() != b.ledger_hash()


class TestDeterminism:
    """P1 — output is independent of input ordering.

    Measured latency fields are observations attached to the projection,
    not projection content; the canonical payload excludes them.
    """

    MEASUREMENT_FIELDS = {"nav_latency_ms", "layout_latency_ms"}

    def _payload(self, granted, tree):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        doc = serializer.serialize(make_request(), granted=granted, nav_tree=tree)
        return json.dumps(
            doc.model_dump(exclude=self.MEASUREMENT_FIELDS), sort_keys=True
        )

    def test_grant_order_does_not_change_projection(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        caps = ["isr.explore", "dash.overview", "deploy.promote"]
        a = serializer.serialize(make_request(), granted=caps, nav_tree=make_nav_tree())
        b = serializer.serialize(make_request(), granted=list(reversed(caps)),
                                 nav_tree=make_nav_tree())
        assert json.dumps(a.model_dump(exclude=self.MEASUREMENT_FIELDS),
                          sort_keys=True) == json.dumps(
            b.model_dump(exclude=self.MEASUREMENT_FIELDS), sort_keys=True
        )

    def test_tree_order_does_not_change_projection(self):
        tree = list(reversed(make_nav_tree()))
        assert self._payload(["dash.overview", "deploy.promote"],
                             make_nav_tree()) == self._payload(
            ["dash.overview", "deploy.promote"], tree
        )

    def test_replay_produces_identical_payload(self):
        assert self._payload(["dash.overview", "lab.candidates"],
                             make_nav_tree()) == self._payload(
            ["dash.overview", "lab.candidates"], make_nav_tree()
        )


class TestRendererEquivalence:
    """P4 — capability/command surfaces identical across backends."""

    RENDERERS = ["react", "terminal", "desktop", "ar"]

    def test_capability_surface_identical_across_renderers(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        surfaces = []
        for renderer in self.RENDERERS:
            doc = serializer.serialize(
                make_request(),
                granted=reg.valid_ids(),
                nav_tree=make_nav_tree(),
                renderer=renderer,
            )
            surfaces.append(doc.capability_surface())
        assert all(s == surfaces[0] for s in surfaces[1:])

    def test_command_surface_identical_across_renderers(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        surfaces = []
        for renderer in self.RENDERERS:
            doc = serializer.serialize(
                make_request(),
                granted=reg.valid_ids(),
                nav_tree=make_nav_tree(),
                renderer=renderer,
            )
            surfaces.append(doc.command_surface())
        assert all(s == surfaces[0] for s in surfaces[1:])

    def test_layout_is_renderer_specific(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        react = serializer.serialize(
            make_request(), granted=reg.valid_ids(),
            nav_tree=make_nav_tree(), renderer="react"
        )
        terminal = serializer.serialize(
            make_request(), granted=reg.valid_ids(),
            nav_tree=make_nav_tree(), renderer="terminal"
        )
        assert react.layout["panels"] != terminal.layout["panels"]
        assert "dock" in react.layout["panels"]
        assert "dock" not in terminal.layout["panels"]

    def test_gated_commands_follow_capabilities(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        doc = serializer.serialize(
            make_request(), granted=["dash.overview", "obs.telemetry"],
            nav_tree=make_nav_tree()
        )
        ids = {c.id for c in doc.commands}
        assert "promote" not in ids
        assert "dismiss" in ids


class TestLatencyBudget:
    """P5 — nav <= 16ms, layout <= 100ms (measured per projection)."""

    def test_budgets_held_across_renderers(self):
        reg = make_registry()
        serializer = UIPMSerializer(PolicyEngine(reg), reg)
        for renderer in ["react", "terminal", "desktop", "ar"]:
            doc = serializer.serialize(
                make_request(),
                granted=reg.valid_ids(),
                nav_tree=make_nav_tree(),
                renderer=renderer,
            )
            assert doc.nav_latency_ms <= 16.0
            assert doc.layout_latency_ms <= 100.0
            assert serializer.within_budgets(doc)
