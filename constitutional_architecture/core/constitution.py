"""
Core Constitution — immutable axioms governing the Evolutionary Software Architecture Platform.

This module contains the canonical constants, the Forbidden Lexicon, and
the constitution version. It is imported by all validators and checkers.

CONSTITUTIONAL: This file itself must never be bypassed by any platform component.
"""

from __future__ import annotations

from enum import Enum, unique

CONSTITUTION_VERSION = "v1.0.0"
CONSTITUTION_TITLE = "Core Constitution of the Evolutionary Software Architecture Platform"

# ==============================================================================
# Axiom definitions
# ==============================================================================

AXIOMS: dict[str, str] = {
    "I": "The ISR Supremacy — The Universal ISR is the single, technology-agnostic source of truth.",
    "II": "The Genome Isolation — The Evolution Engine operates exclusively on the Architecture Genome.",
    "III": "The Compiler Purity — All compiler backends are pure functions: f(ISR, Target, Constraints) -> Artifacts.",
    "IV": "The Knowledge Externality — Architectural patterns reside in the CKB, never hardcoded.",
    "V": "The Dual-Track Evolution — Functional and non-functional requirements evolve in parallel.",
    "VI": "The Boundary Integrity — The 10-pass pipeline is the only permitted path through the system.",
    "VII": "The Auditability Principle — Every transformation must be recorded and traceable.",
}


@unique
class Axiom(str, Enum):
    ISR_SUPREMACY = "I"
    GENOME_ISOLATION = "II"
    COMPILER_PURITY = "III"
    KNOWLEDGE_EXTERNALITY = "IV"
    DUAL_TRACK_EVOLUTION = "V"
    BOUNDARY_INTEGRITY = "VI"
    AUDITABILITY = "VII"


# ==============================================================================
# The Forbidden Lexicon (Appendix A of the Core Constitution)
# ==============================================================================
# These terms must never appear in ISR entity values, field names, or schema
# definitions. They ARE permitted in Compiler Backend implementations.
# ==============================================================================

FORBIDDEN_CLOUD_PROVIDERS: tuple[str, ...] = (
    "aws", "azure", "gcp", "digitalocean", "heroku", "netlify",
    "vercel", "cloudflare", "alibaba",
)

FORBIDDEN_DATABASES: tuple[str, ...] = (
    "postgresql", "postgres", "mysql", "mariadb", "sqlite",
    "mongodb", "dynamodb", "cassandra", "redis", "elasticsearch",
    "cockroachdb", "spanner",
)

FORBIDDEN_UI_FRAMEWORKS: tuple[str, ...] = (
    "react", "vue", "svelte", "angular", "ember", "solidjs",
    "qwik", "lit", "flutter", "swiftui",
)

FORBIDDEN_API_FRAMEWORKS: tuple[str, ...] = (
    "fastapi", "express", "django", "flask", "spring", "rails",
    "laravel", "aspnet", "gin", "echo",
)

FORBIDDEN_IAC: tuple[str, ...] = (
    "terraform", "pulumi", "cloudformation", "cdk", "helm",
    "kustomize", "ansible", "chef", "puppet",
)

FORBIDDEN_STYLING: tuple[str, ...] = (
    "tailwind", "bootstrap", "material-ui", "chakra",
    "styled-components", "sass", "less", "postcss",
)

FORBIDDEN_ORCHESTRATION: tuple[str, ...] = (
    "kubernetes", "k8s", "docker", "ecs", "eks", "gke", "aks",
    "lambda", "functions", "fargate",
)

FORBIDDEN_LEXICON: tuple[str, ...] = (
    FORBIDDEN_CLOUD_PROVIDERS
    + FORBIDDEN_DATABASES
    + FORBIDDEN_UI_FRAMEWORKS
    + FORBIDDEN_API_FRAMEWORKS
    + FORBIDDEN_IAC
    + FORBIDDEN_STYLING
    + FORBIDDEN_ORCHESTRATION
)

# ==============================================================================
# Pass definitions (Axiom VI)
# ==============================================================================

PASSES: list[dict[str, str]] = [
    {"number": "1", "name": "Requirements Validation",
     "input": "Raw Input", "output": "Validated Requirement Graph"},
    {"number": "2", "name": "Intent Analysis",
     "input": "Requirement Graph", "output": "Intent Model"},
    {"number": "3", "name": "Topology Resolution",
     "input": "Intent Model + CKB", "output": "Architectural Profile"},
    {"number": "4", "name": "Genome Construction",
     "input": "Architectural Profile", "output": "Architecture Genome"},
    {"number": "5", "name": "Dual-Track Evolution",
     "input": "Genome + Constitution", "output": "Optimized Genome"},
    {"number": "6", "name": "ISR Instantiation",
     "input": "Optimized Genome", "output": "Universal ISR"},
    {"number": "7", "name": "Verification",
     "input": "Universal ISR", "output": "Verification Report"},
    {"number": "8", "name": "Backend Selection",
     "input": "ISR + Constraints", "output": "Compiler Targets"},
    {"number": "9", "name": "Code Generation",
     "input": "ISR + Targets", "output": "Source Artifacts"},
    {"number": "10", "name": "Runtime Instrumentation",
     "input": "Generated Artifacts", "output": "Deployable System"},
]

# ==============================================================================
# Minimum evaluator requirements (Axiom V)
# ==============================================================================

MINIMUM_FUNCTIONAL_EVALUATORS: int = 1
MINIMUM_NON_FUNCTIONAL_EVALUATORS: int = 1
MINIMUM_CONSTITUTIONAL_THRESHOLD: float = 0.60
