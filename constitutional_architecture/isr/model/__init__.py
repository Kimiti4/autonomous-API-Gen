"""ISR object model — technology-neutral architectural representations."""

from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.model.edges import (
    EdgeType, CouplingStrength, CommunicationMode, Criticality,
    EdgeAttributes, EdgeDefinition, EDGE_DEFINITIONS
)
from constitutional_architecture.isr.model.fields import (
    FieldType, FieldCardinality, FieldConstraint, Field
)
from constitutional_architecture.isr.model.constraints import (
    Constraint, ConstraintScope, ConstraintSeverity
)
from constitutional_architecture.isr.model.entity import Entity, Relationship
from constitutional_architecture.isr.model.event import Event, EventPattern, EventGuarantee
from constitutional_architecture.isr.model.service import Service, Operation, OperationType, ServiceDependency
from constitutional_architecture.isr.model.workflow import Workflow, WorkflowState, WorkflowTransition, StateType
from constitutional_architecture.isr.model.policy import Policy, PolicyType, PolicyRule, Permission
from constitutional_architecture.isr.model.interface import Interface, InterfaceType, HttpMethod, Endpoint
from constitutional_architecture.isr.model.deployment import (
    Deployment, ScalingConfig, ScalingStrategy, EnvironmentTier,
    NetworkingConfig, MonitoringConfig, StorageConfig, SecretsConfig
)
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.semantics.temporal import (
    TemporalConstraint, TemporalConstraintKind, TemporalValidationError,
    project_temporal_evidence, project_temporal_semantics,
    validate_module_temporal_constraints,
)
from constitutional_architecture.isr.semantics.capability import (
    BusinessCapability, CapabilityValidationError,
    project_business_capabilities, validate_system_capability_constraints,
)
from constitutional_architecture.isr.semantics.migration import (
    CompatibilityPolicy, DataMigrationIntent, MigrationValidationError,
    assert_migration_technology_agnostic, migration_mechanism_hits,
    project_data_migrations, validate_module_migration_constraints,
)
from constitutional_architecture.isr.semantics.reliability import (
    DegradationPolicy, FailureMode, RecoveryBehavior, RecoveryObjective,
    ReliabilityRequirement, ReliabilityValidationError,
    assert_reliability_technology_agnostic, project_reliability_requirements,
    reliability_mechanism_hits, validate_system_reliability_constraints,
)
from constitutional_architecture.isr.semantics.boundary import (
    ArchitecturalBoundary, BoundaryValidationError,
    assert_boundary_technology_agnostic, boundary_mechanism_hits,
    project_architectural_boundaries, validate_system_boundary_constraints,
)
from constitutional_architecture.isr.semantics.deployment import (
    DeploymentIntent, DeploymentValidationError, RolloutStrategy,
    assert_deployment_technology_agnostic, deployment_mechanism_hits,
    project_deployment_intents, validate_system_deployment_constraints,
)
from constitutional_architecture.isr.semantics.requirement import (
    AcceptanceCriterion, ObligationKind, Requirement, RequirementValidationError,
    assert_requirement_technology_agnostic, project_acceptance_criteria,
    project_requirements, requirement_mechanism_hits,
    validate_system_requirement_constraints,
)
from constitutional_architecture.isr.semantics.testing_anchor import (
    AnchorAuthority, ProtectionPolicy, TestingAnchor, TestingAnchorValidationError,
    assert_testing_technology_agnostic, project_testing_anchors,
    testing_mechanism_hits, validate_system_testing_anchor_constraints,
)
from constitutional_architecture.isr.semantics.documentation import (
    DocumentationAudience, DocumentationIntent, DocumentationPurpose,
    DocumentationValidationError, assert_documentation_technology_agnostic,
    documentation_mechanism_hits, project_documentation_intents,
    validate_system_documentation_constraints,
)
from constitutional_architecture.isr.completeness import CompletenessLevel

__all__ = [
    "NodeType",
    "EdgeType", "CouplingStrength", "CommunicationMode", "Criticality",
    "EdgeAttributes", "EdgeDefinition", "EDGE_DEFINITIONS",
    "FieldType", "FieldCardinality", "FieldConstraint", "Field",
    "Constraint", "ConstraintScope", "ConstraintSeverity",
    "Entity", "Relationship",
    "Event", "EventPattern", "EventGuarantee",
    "Service", "Operation", "OperationType", "ServiceDependency",
    "Workflow", "WorkflowState", "WorkflowTransition", "StateType",
    "Policy", "PolicyType", "PolicyRule", "Permission",
    "Interface", "InterfaceType", "HttpMethod", "Endpoint",
    "Deployment", "ScalingConfig", "ScalingStrategy", "EnvironmentTier",
    "NetworkingConfig", "MonitoringConfig", "StorageConfig", "SecretsConfig",
    "Module", "System", "SystemMetadata", "ISR", "ISRProvenance",
    "TemporalConstraint", "TemporalConstraintKind", "TemporalValidationError",
    "project_temporal_evidence", "project_temporal_semantics",
    "validate_module_temporal_constraints",
    "BusinessCapability", "CapabilityValidationError",
    "project_business_capabilities", "validate_system_capability_constraints",
    "CompatibilityPolicy", "DataMigrationIntent", "MigrationValidationError",
    "assert_migration_technology_agnostic", "migration_mechanism_hits",
    "project_data_migrations", "validate_module_migration_constraints",
    "DegradationPolicy", "FailureMode", "RecoveryBehavior", "RecoveryObjective",
    "ReliabilityRequirement", "ReliabilityValidationError",
    "assert_reliability_technology_agnostic", "project_reliability_requirements",
    "reliability_mechanism_hits", "validate_system_reliability_constraints",
    "ArchitecturalBoundary", "BoundaryValidationError",
    "assert_boundary_technology_agnostic", "boundary_mechanism_hits",
    "project_architectural_boundaries", "validate_system_boundary_constraints",
    "DeploymentIntent", "DeploymentValidationError", "RolloutStrategy",
    "assert_deployment_technology_agnostic", "deployment_mechanism_hits",
    "project_deployment_intents", "validate_system_deployment_constraints",
    "AcceptanceCriterion", "ObligationKind", "Requirement",
    "RequirementValidationError",
    "assert_requirement_technology_agnostic", "project_acceptance_criteria",
    "project_requirements", "requirement_mechanism_hits",
    "validate_system_requirement_constraints",
    "AnchorAuthority", "ProtectionPolicy", "TestingAnchor",
    "TestingAnchorValidationError",
    "assert_testing_technology_agnostic", "project_testing_anchors",
    "testing_mechanism_hits", "validate_system_testing_anchor_constraints",
    "DocumentationAudience", "DocumentationIntent", "DocumentationPurpose",
    "DocumentationValidationError",
    "assert_documentation_technology_agnostic", "documentation_mechanism_hits",
    "project_documentation_intents", "validate_system_documentation_constraints",
    "CompletenessLevel",
]