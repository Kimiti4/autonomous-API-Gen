"""
ISR — Intermediate Software Representation

The ISR is the constitutional source of truth for all software architecture
within the platform. It represents requirements traceability, business
capabilities, domains, services, components, APIs, events, data models,
security policies, infrastructure, deployment topology, and all other
architectural concerns.

ISR instances are immutable. Every mutation produces a new version.
"""

from constitutional_architecture.isr.model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    Field, Operation,
    EdgeType, NodeType,
    ISR, ISRProvenance,
    CompletenessLevel,
)
from constitutional_architecture.isr.graph import (
    TypedGraph, GraphNode, GraphEdge, GraphOperations, GraphTraversal, GraphQueries,
)
from constitutional_architecture.isr.isr_graph import ISRGraph, ISRNode, ISREdge
from constitutional_architecture.isr.types import ArchitecturalTypeSystem, TypeChecker
from constitutional_architecture.isr.validation import Validator, ValidationResult, Diagnostic, DiagnosticSeverity
from constitutional_architecture.isr.serialization import ISRSerializer, ISRDeserializer
from constitutional_architecture.isr.versioning import ISRVersion, LineageTracker, ContentHasher
from constitutional_architecture.isr.diff import StructuralDiff, StructuralDiffResult, SemanticDiff, SemanticDiffResult
from constitutional_architecture.isr.metrics import StaticFitnessEvaluator
from constitutional_architecture.isr.irr import IRR, Requirement, RequirementType
from constitutional_architecture.isr.eir import EIR, Transformation, MutationCategory, MutationClass
from constitutional_architecture.isr.completeness import CompletenessLevel as CL, CompletenessChecker

__all__ = [
    "System", "Module", "Entity", "Service", "Workflow", "Policy",
    "Interface", "Event", "Deployment", "Constraint",
    "Field", "Operation",
    "EdgeType", "NodeType",
    "ISR", "ISRProvenance",
    "ISRGraph", "ISRNode", "ISREdge",
    "TypedGraph", "GraphNode", "GraphEdge", "GraphOperations", "GraphTraversal", "GraphQueries",
    "ArchitecturalTypeSystem", "TypeChecker",
    "Validator", "ValidationResult", "Diagnostic", "DiagnosticSeverity",
    "ISRSerializer", "ISRDeserializer",
    "ISRVersion", "LineageTracker", "ContentHasher",
    "StructuralDiff", "StructuralDiffResult", "SemanticDiff", "SemanticDiffResult",
    "StaticFitnessEvaluator",
    "IRR", "Requirement", "RequirementType",
    "EIR", "Transformation", "MutationCategory", "MutationClass",
    "CompletenessLevel", "CompletenessChecker",
]
