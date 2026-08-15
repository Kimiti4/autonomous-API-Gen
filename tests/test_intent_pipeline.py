"""
Phase 1 Exit Gate Tests — Merged Intent Pipeline (Option 1 + Option 2).

Covers:
  - IntentModel (Option 2 rich model) creation, validation, security consistency
  - sanitize_forbidden_terms() constitutional gate
  - RequirementsValidator (Pass 1) — completeness, ambiguity, forbidden lexicon
  - IntentAnalyzer (Pass 2) — archetype/capability/persona detection, multi-agent enrichment
  - IntentValidator — technology neutrality, security by design, observability by design
  - RequirementsGraph — nodes, edges, cycle detection, conflict detection, impact analysis
  - ProductTopologyResolver (Pass 3) — IntentModel + CKB → Genome seed
  - Full pipeline integration: Pass 1 → Pass 2 → IntentValidator → Pass 3
"""

import pytest

from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, ComplianceStandard, IntentModel,
    OperationalConstraint, Persona, QualityAttribute, sanitize_forbidden_terms,
)
from constitutional_architecture.core.models.requirements_graph import (
    EdgeType, NodeType as ReqNodeType, RequirementEdge, RequirementNode,
    RequirementsGraph,
)
from constitutional_architecture.engine.passes.intent_validation_pass import (
    RequirementsValidator, ValidationIssue,
)
from constitutional_architecture.core.pipeline.intent_analyzer import (
    IntentAnalyzer, IntentAnalysisError, RequirementsValidationError,
)
from constitutional_architecture.validators.intent_validator import (
    IntentConstitutionalViolation, IntentValidator,
)
from constitutional_architecture.engine.bridges.topology_bridge import (
    ProductTopologyResolver,
)


# ══════════════════════════════════════════════════════════════════════════════
# IntentModel (Option 2 rich model)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentModel:
    def test_valid_model_creation(self):
        model = IntentModel(
            project_name="ProjectFlow",
            problem_statement="A multi-tenant project management platform.",
            personas=[Persona(name="Admin", role="manager", primary_goals=["Track progress"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="Task Management", description="Manage tasks", priority=0.9)],
        )
        assert model.business_archetype == BusinessArchetype.B2B_SAAS
        assert len(model.personas) == 1
        assert len(model.core_capabilities) == 1
        assert model.authentication_required is True
        assert model.structured_logging_required is True

    def test_default_quality_weights_have_all_16(self):
        model = IntentModel(
            project_name="P",
            problem_statement="Build something.",
            personas=[Persona(name="U", role="user", primary_goals=["G"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
        )
        assert len(model.quality_priorities) == 16
        for attr in QualityAttribute:
            assert model.quality_priorities[attr] == 0.5

    def test_invalid_quality_weight_raises(self):
        with pytest.raises(ValueError):
            IntentModel(
                project_name="P", problem_statement="Test",
                personas=[Persona(name="U", role="user", primary_goals=["G"])],
                business_archetype=BusinessArchetype.B2B_SAAS,
                core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
                quality_priorities={QualityAttribute.SECURITY: 1.5},
            )

    def test_hipaa_enforces_encryption(self):
        with pytest.raises(ValueError, match="HIPAA"):
            IntentModel(
                project_name="HealthApp", problem_statement="Patient records.",
                personas=[Persona(name="Doc", role="clinician", primary_goals=["View"])],
                business_archetype=BusinessArchetype.HEALTHCARE,
                core_capabilities=[Capability(name="Records", description="Patient data", priority=0.9)],
                compliance_standards=[ComplianceStandard.HIPAA],
                encryption_at_rest=False,
            )

    def test_pci_enforces_transit_encryption(self):
        with pytest.raises(ValueError, match="PCI-DSS"):
            IntentModel(
                project_name="Pay", problem_statement="Payments.",
                personas=[Persona(name="U", role="user", primary_goals=["Pay"])],
                business_archetype=BusinessArchetype.FINTECH,
                core_capabilities=[Capability(name="Pay", description="Pay", priority=0.9)],
                compliance_standards=[ComplianceStandard.PCI_DSS],
                encryption_in_transit=False,
            )

    def test_multi_agent_enrichment_tracking(self):
        model = IntentModel(
            project_name="P", problem_statement="Test",
            personas=[Persona(name="U", role="user", primary_goals=["G"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
            enrichment_agents=["IntentAnalyzer"],
            confidence_score=0.7,
        )
        assert "IntentAnalyzer" in model.enrichment_agents
        assert model.confidence_score == 0.7

    def test_authorization_model_validation(self):
        with pytest.raises(Exception):
            IntentModel(
                project_name="P", problem_statement="Test",
                personas=[Persona(name="U", role="user", primary_goals=["G"])],
                business_archetype=BusinessArchetype.B2B_SAAS,
                core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
                authorization_model="invalid",
            )


# ══════════════════════════════════════════════════════════════════════════════
# sanitize_forbidden_terms() constitutional gate
# ══════════════════════════════════════════════════════════════════════════════

class TestSanitizeForbiddenTerms:
    def test_react_becomes_abstract(self):
        assert "component_framework" in sanitize_forbidden_terms("Build a React app").lower()

    def test_aws_becomes_abstract(self):
        assert "cloud_provider" in sanitize_forbidden_terms("Deploy on AWS").lower()

    def test_docker_becomes_abstract(self):
        assert "container_runtime" in sanitize_forbidden_terms("Use Docker").lower()

    def test_clean_text_passes(self):
        assert sanitize_forbidden_terms("A scalable platform") == "A scalable platform"

    def test_case_insensitive_replacement(self):
        result = sanitize_forbidden_terms("REACT and POSTGRES")
        assert "component_framework" in result
        assert "relational_database" in result


# ══════════════════════════════════════════════════════════════════════════════
# RequirementsValidator (Pass 1)
# ══════════════════════════════════════════════════════════════════════════════

class TestRequirementsValidator:
    def setup_method(self):
        self.validator = RequirementsValidator()

    def test_valid_requirement_passes(self):
        result = self.validator.validate("req-001",
            "Build a multi-tenant project management tool for enterprise teams. "
            "Users include admins and team members. Must support task assignment and reporting."
        )
        assert result.is_valid is True
        assert result.requirement_id == "req-001"

    def test_empty_input_fails(self):
        result = self.validator.validate("req-002", "")
        assert result.is_valid is False
        assert any("empty" in i.message.lower() for i in result.issues)

    def test_ambiguity_detected(self):
        result = self.validator.validate("req-003",
            "Maybe build something like a tool, etc."
        )
        assert any(i.severity == "warning" for i in result.issues)

    def test_forbidden_lexicon_flagged(self):
        result = self.validator.validate("req-004",
            "Build a React frontend with PostgreSQL on AWS."
        )
        tech_issues = [i for i in result.issues if i.field == "technology_neutrality"]
        assert len(tech_issues) >= 2

    def test_sanitized_input_produced(self):
        result = self.validator.validate("req-005",
            "Build a React dashboard deployed on AWS."
        )
        assert "react" not in result.sanitized_input.lower()

    def test_extracted_sections(self):
        result = self.validator.validate("req-006",
            "We need to build a user management system. "
            "Users need authentication and role-based access. "
            "Must support user CRUD."
        )
        assert "problem_description" in result.extracted_sections
        assert "target_users" in result.extracted_sections
        assert "core_capabilities" in result.extracted_sections


# ══════════════════════════════════════════════════════════════════════════════
# IntentAnalyzer (Pass 2) — Option 2 extraction + Option 1 enrichment
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentAnalyzer:
    def setup_method(self):
        self.validator = RequirementsValidator()
        self.analyzer = IntentAnalyzer()

    def _make_valid_req(self, text: str) -> str:
        return self.validator.validate("test-req", text)

    def test_produces_technology_neutral_intent(self):
        req = self._make_valid_req(
            "Build a multi-tenant AI analytics SaaS for healthcare. "
            "Users are data analysts and administrators. "
            "Must support subscription billing and HIPAA compliance."
        )
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.B2B_SAAS
        assert intent.confidence_score > 0.0
        # Check no forbidden terms leaked
        text = intent.model_dump_json().lower()
        assert "react" not in text
        assert "postgres" not in text

    def test_detects_marketplace_archetype(self):
        req = self._make_valid_req("A marketplace connecting buyers and sellers with listings.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.MARKETPLACE

    def test_detects_ecommerce_archetype(self):
        req = self._make_valid_req("Build an online store with shopping cart and checkout.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.E_COMMERCE

    def test_detects_internal_tool_archetype(self):
        req = self._make_valid_req("Internal admin panel for employee workflow.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.INTERNAL_TOOL

    def test_detects_data_platform_archetype(self):
        req = self._make_valid_req("Analytics dashboard with KPIs and real-time metrics.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.DATA_PLATFORM

    def test_detects_ai_archetype(self):
        req = self._make_valid_req("An AI/ML model serving platform for predictions.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.AI_APPLICATION

    def test_detects_healthcare_archetype(self):
        req = self._make_valid_req("Healthcare patient management system.")
        intent = self.analyzer.analyze(req)
        assert intent.business_archetype == BusinessArchetype.HEALTHCARE

    def test_capabilities_extracted(self):
        req = self._make_valid_req(
            "Build a platform with user authentication, billing, and notifications."
        )
        intent = self.analyzer.analyze(req)
        cap_names = [c.name for c in intent.core_capabilities]
        assert "User Authentication" in cap_names
        assert "Billing Management" in cap_names
        assert "Notifications" in cap_names

    def test_personas_extracted(self):
        req = self._make_valid_req(
            "For admin users and developers who need API access."
        )
        intent = self.analyzer.analyze(req)
        roles = [p.role for p in intent.personas]
        assert "admin" in roles
        assert "developer" in roles

    def test_compliance_detected(self):
        req = self._make_valid_req("Must comply with GDPR and HIPAA regulations.")
        intent = self.analyzer.analyze(req)
        assert ComplianceStandard.GDPR in intent.compliance_standards
        assert ComplianceStandard.HIPAA in intent.compliance_standards

    def test_operational_constraints_detected(self):
        req = self._make_valid_req("Offline-first mobile app with real-time sync.")
        intent = self.analyzer.analyze(req)
        assert OperationalConstraint.OFFLINE_FIRST in intent.operational_constraints
        assert OperationalConstraint.REAL_TIME in intent.operational_constraints

    def test_saas_quality_priorities(self):
        req = self._make_valid_req("A multi-tenant B2B SaaS platform.")
        intent = self.analyzer.analyze(req)
        assert intent.quality_priorities[QualityAttribute.SECURITY] == 0.9
        assert intent.quality_priorities[QualityAttribute.SCALABILITY] == 0.8
        assert intent.quality_priorities[QualityAttribute.RELIABILITY] == 0.85

    def test_multi_agent_enrichment(self):
        req = self._make_valid_req("Build a marketplace.")
        intent = self.analyzer.analyze(req)
        initial_conf = intent.confidence_score

        enriched = self.analyzer.enrich(intent, "SecurityAgent", {
            "regulatory_constraints": [],
        })
        assert enriched.confidence_score > initial_conf
        assert "SecurityAgent" in enriched.enrichment_agents

    def test_rejects_invalid_requirements(self):
        invalid_req = self.validator.validate("bad-req", "")
        with pytest.raises(ValueError, match="invalid"):
            self.analyzer.analyze(invalid_req)


# ══════════════════════════════════════════════════════════════════════════════
# IntentValidator — constitutional gate between Pass 2 and Pass 3
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentValidator:
    def setup_method(self):
        self.validator = IntentValidator()

    def _make_intent(self, **overrides) -> IntentModel:
        params = dict(
            project_name="Test", problem_statement="A platform.",
            personas=[Persona(name="U", role="user", primary_goals=["G"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
        )
        params.update(overrides)
        return IntentModel(**params)

    def test_valid_intent_passes(self):
        intent = self._make_intent()
        self.validator.validate(intent)  # should not raise

    def test_security_by_design_violation(self):
        intent = self._make_intent(authorization_model="none")
        with pytest.raises(IntentConstitutionalViolation, match="authorization"):
            self.validator.validate(intent)

    def test_observability_logging_non_negotiable(self):
        intent = self._make_intent(structured_logging_required=False)
        with pytest.raises(IntentConstitutionalViolation, match="Structured logging"):
            self.validator.validate(intent)

    def test_observability_health_checks_non_negotiable(self):
        intent = self._make_intent(health_checks_required=False)
        with pytest.raises(IntentConstitutionalViolation, match="Health checks"):
            self.validator.validate(intent)

    def test_restricted_capability_requires_encryption(self):
        intent = self._make_intent(
            core_capabilities=[Capability(name="Secret", description="X", priority=0.9,
                                          security_classification="restricted")],
            encryption_at_rest=False,
        )
        with pytest.raises(IntentConstitutionalViolation, match="encryption at rest"):
            self.validator.validate(intent)

    def test_quality_completeness(self):
        intent = self._make_intent(quality_priorities={})
        with pytest.raises(IntentConstitutionalViolation, match="missing"):
            self.validator.validate(intent)

    def test_capability_coherence(self):
        intent = self._make_intent(
            core_capabilities=[Capability(name="A", description="X", priority=0.5,
                                          dependencies=["NonExistent"])],
        )
        with pytest.raises(IntentConstitutionalViolation, match="unknown capability"):
            self.validator.validate(intent)


# ══════════════════════════════════════════════════════════════════════════════
# RequirementsGraph — intermediate IR between IntentModel and ArchitectureGenome
# ══════════════════════════════════════════════════════════════════════════════

class TestRequirementsGraph:
    def test_add_nodes_and_edges(self):
        g = RequirementsGraph()
        g.add_node(RequirementNode(id="n1", type=ReqNodeType.CAPABILITY, label="Cap A"))
        g.add_node(RequirementNode(id="n2", type=ReqNodeType.CAPABILITY, label="Cap B"))
        g.add_edge(RequirementEdge(source="n1", target="n2", type=EdgeType.DEPENDS_ON))
        assert "n1" in g.nodes
        assert "n2" in g.nodes
        assert len(g.edges) == 1

    def test_duplicate_node_raises(self):
        g = RequirementsGraph()
        g.add_node(RequirementNode(id="n1", type=ReqNodeType.PERSONA, label="P"))
        with pytest.raises(ValueError, match="already exists"):
            g.add_node(RequirementNode(id="n1", type=ReqNodeType.PERSONA, label="P"))

    def test_cycle_detection(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="c", target="a", type=EdgeType.DEPENDS_ON))
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_acyclic_graph_no_cycles(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        assert g.detect_cycles() == []

    def test_transitive_dependencies(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        deps = g.transitive_dependencies("a")
        assert "b" in deps
        assert "c" in deps

    def test_transitive_dependents(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="c", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        deps = g.transitive_dependents("c")
        assert "a" in deps
        assert "b" in deps

    def test_conflict_detection(self):
        g = RequirementsGraph()
        g.add_node(RequirementNode(id="a", type=ReqNodeType.CAPABILITY, label="A"))
        g.add_node(RequirementNode(id="b", type=ReqNodeType.CAPABILITY, label="B"))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.CONFLICTS_WITH))
        conflicts = g.detect_conflicts()
        assert len(conflicts) == 1
        assert "Conflict" in conflicts[0].message

    def test_impact_analysis(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="c", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        impact = g.impact_analysis("c")
        assert "a" in impact.affected_nodes or "b" in impact.affected_nodes

    def test_topological_sort(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        order = g.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_topological_sort_with_cycle_raises(self):
        g = RequirementsGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(RequirementNode(id=nid, type=ReqNodeType.CAPABILITY, label=nid))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="c", target="a", type=EdgeType.DEPENDS_ON))
        with pytest.raises(ValueError, match="Cycle"):
            g.topological_sort()

    def test_validate_reports_errors(self):
        g = RequirementsGraph()
        g.add_node(RequirementNode(id="a", type=ReqNodeType.CAPABILITY, label="A"))
        g.add_node(RequirementNode(id="b", type=ReqNodeType.CAPABILITY, label="B"))
        g.add_node(RequirementNode(id="c", type=ReqNodeType.CAPABILITY, label="C"))
        g.add_edge(RequirementEdge(source="a", target="b", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="b", target="c", type=EdgeType.DEPENDS_ON))
        g.add_edge(RequirementEdge(source="c", target="a", type=EdgeType.DEPENDS_ON))
        issues = g.validate()
        assert any("Circular" in i.message for i in issues)

    def test_get_nodes_by_type(self):
        g = RequirementsGraph()
        g.add_node(RequirementNode(id="c1", type=ReqNodeType.CAPABILITY, label="C1"))
        g.add_node(RequirementNode(id="c2", type=ReqNodeType.CAPABILITY, label="C2"))
        g.add_node(RequirementNode(id="p1", type=ReqNodeType.PERSONA, label="P1"))
        assert len(g.get_nodes_by_type(ReqNodeType.CAPABILITY)) == 2
        assert len(g.get_nodes_by_type(ReqNodeType.PERSONA)) == 1


# ══════════════════════════════════════════════════════════════════════════════
# ProductTopologyResolver (Pass 3)
# ══════════════════════════════════════════════════════════════════════════════

class TestProductTopologyResolver:
    def test_resolves_b2b_saas_to_genome(self):
        resolver = ProductTopologyResolver()
        intent = IntentModel(
            project_name="SaaSApp", problem_statement="Multi-tenant SaaS platform",
            personas=[Persona(name="Admin", role="admin", primary_goals=["Manage"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="Auth", description="Login", priority=0.9)],
        )
        result = resolver.resolve(intent)
        assert result.archetype == BusinessArchetype.B2B_SAAS
        assert result.genome is not None
        assert len(result.requirements_graph.nodes) > 0

    def test_resolves_data_dashboard_genome(self):
        resolver = ProductTopologyResolver()
        intent = IntentModel(
            project_name="Dash", problem_statement="Analytics dashboard with KPIs",
            personas=[Persona(name="Analyst", role="analyst", primary_goals=["View"])],
            business_archetype=BusinessArchetype.DATA_PLATFORM,
            core_capabilities=[Capability(name="Reporting", description="Reports", priority=0.9)],
        )
        result = resolver.resolve(intent)
        assert result.archetype == BusinessArchetype.DATA_PLATFORM
        assert result.genome.structure.density_profile.allele >= 0.5

    def test_builds_requirements_graph(self):
        resolver = ProductTopologyResolver()
        intent = IntentModel(
            project_name="Test", problem_statement="A platform with auth and billing",
            personas=[Persona(name="Admin", role="admin", primary_goals=["M"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[
                Capability(name="Auth", description="Login", priority=0.9),
                Capability(name="Billing", description="Pay", priority=0.8),
            ],
        )
        result = resolver.resolve(intent)
        graph = result.requirements_graph
        assert len(graph.get_nodes_by_type(ReqNodeType.CAPABILITY)) >= 2
        assert len(graph.get_nodes_by_type(ReqNodeType.PERSONA)) >= 1
        assert len(graph.get_nodes_by_type(ReqNodeType.QUALITY_ATTRIBUTE)) >= 5

    def test_quality_profile_included(self):
        resolver = ProductTopologyResolver()
        intent = IntentModel(
            project_name="Secure", problem_statement="Secure platform",
            personas=[Persona(name="U", role="user", primary_goals=["G"])],
            business_archetype=BusinessArchetype.B2B_SAAS,
            core_capabilities=[Capability(name="X", description="Y", priority=0.5)],
            quality_priorities={
                QualityAttribute.SECURITY: 0.9,
                QualityAttribute.PERFORMANCE: 0.7,
            },
        )
        result = resolver.resolve(intent)
        assert result.quality_profile["security"] == 0.9
        assert result.quality_profile["performance"] == 0.7


# ══════════════════════════════════════════════════════════════════════════════
# Full Pipeline Integration: Pass 1 → Pass 2 → IntentValidator → Pass 3
# ══════════════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    def test_raw_text_to_genome(self):
        pass_1 = RequirementsValidator()
        analyzer = IntentAnalyzer()
        intent_validator = IntentValidator()
        resolver = ProductTopologyResolver()

        raw = "Build a secure analytics dashboard for enterprise customers with real-time metrics"

        v_result = pass_1.validate("pipeline-test", raw)
        assert v_result.is_valid

        intent = analyzer.analyze(v_result)
        intent_validator.validate(intent)

        topology = resolver.resolve(intent)
        assert topology.genome is not None
        assert topology.archetype == BusinessArchetype.DATA_PLATFORM

    def test_forbidden_term_sanitized_through_pipeline(self):
        pass_1 = RequirementsValidator()
        analyzer = IntentAnalyzer()

        v_result = pass_1.validate("sanitize-test",
            "Build a React dashboard deployed on AWS"
        )
        assert "react" not in v_result.sanitized_input.lower()
        assert "aws" not in v_result.sanitized_input.lower()

        intent = analyzer.analyze(v_result)
        text = intent.problem_statement.lower()
        assert "component_framework" in text
        assert "cloud_provider" in text

    def test_constitutional_violation_rejected(self):
        pass_1 = RequirementsValidator()
        analyzer = IntentAnalyzer()
        intent_validator = IntentValidator()

        v_result = pass_1.validate("sec-test",
            "Build a platform with structured_logging_required=False"
        )
        intent = analyzer.analyze(v_result)
        # Force a violation
        intent.structured_logging_required = False
        with pytest.raises(IntentConstitutionalViolation, match="Structured logging"):
            intent_validator.validate(intent)

    def test_multi_agent_enrichment_pipeline(self):
        analyzer = IntentAnalyzer()
        pass_1 = RequirementsValidator()

        v_result = pass_1.validate("enrich-test", "Build a marketplace platform")
        intent = analyzer.analyze(v_result)
        assert intent.confidence_score == 0.7

        intent = analyzer.enrich(intent, "UXAgent", {"quality_priorities": intent.quality_priorities})
        assert intent.confidence_score > 0.7
        assert "UXAgent" in intent.enrichment_agents

        intent = analyzer.enrich(intent, "SecurityAgent", {"quality_priorities": intent.quality_priorities})
        assert intent.confidence_score > 0.75
        assert len(intent.enrichment_agents) == 3  # IntentAnalyzer + UXAgent + SecurityAgent

    def test_requirements_graph_through_pipeline(self):
        pass_1 = RequirementsValidator()
        analyzer = IntentAnalyzer()
        resolver = ProductTopologyResolver()

        v_result = pass_1.validate("graph-test",
            "Build a platform with user authentication and billing. "
            "Admin users manage billing. Developers use the API."
        )
        intent = analyzer.analyze(v_result)
        result = resolver.resolve(intent)

        graph = result.requirements_graph
        cycles = graph.detect_cycles()
        assert cycles == []  # No cycles in well-formed requirements

        issues = graph.validate()
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_analyze_from_dict(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze_from_dict({
            "project_name": "DictApp",
            "problem_statement": "Build a multi-tenant SaaS platform with billing for enterprise teams.",
        })
        assert intent.project_name == "DictApp"
        assert intent.business_archetype == BusinessArchetype.B2B_SAAS
        assert len(intent.personas) >= 1
        assert len(intent.core_capabilities) >= 1

    def test_analyze_from_dict_missing_fields_raises(self):
        analyzer = IntentAnalyzer()
        with pytest.raises(RequirementsValidationError):
            analyzer.analyze_from_dict({"project_name": "Empty"})
