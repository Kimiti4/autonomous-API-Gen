"""
Mutation Taxonomy.

Classifies all architectural transformations by category and class.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class MutationCategory(str, Enum):
    """High-level category of architectural mutation."""

    STRUCTURAL = "structural"
    TOPOLOGICAL = "topological"
    STRATEGIC = "strategic"
    BEHAVIOURAL = "behavioural"
    OPERATIONAL = "operational"
    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"

    def __str__(self) -> str:
        return self.value


@unique
class MutationClass(str, Enum):
    """
    Structural class of mutation (determines ISR impact and risk).

    - STRUCTURAL: Changes graph topology (high risk)
    - STRATEGIC: Changes node attributes / chromosome family (medium risk)
    - ADDITIVE: Adds nodes/edges (low risk)
    - PARAMETRIC: Changes attribute values (low risk)
    - TOPOLOGICAL: Changes edge types (medium-high risk)
    """

    STRUCTURAL = "structural"
    STRATEGIC = "strategic"
    ADDITIVE = "additive"
    PARAMETRIC = "parametric"
    TOPOLOGICAL = "topological"

    def __str__(self) -> str:
        return self.value

    @property
    def risk_level(self) -> str:
        risk_map = {
            MutationClass.STRUCTURAL: "high",
            MutationClass.STRATEGIC: "medium",
            MutationClass.ADDITIVE: "low",
            MutationClass.PARAMETRIC: "low",
            MutationClass.TOPOLOGICAL: "medium_high",
        }
        return risk_map[self]

    @property
    def requires_revalidation(self) -> bool:
        return self in {MutationClass.STRUCTURAL, MutationClass.TOPOLOGICAL}


KNOWN_TRANSFORMATIONS: dict[str, tuple[MutationCategory, MutationClass, str]] = {
    "split_module": (MutationCategory.STRUCTURAL, MutationClass.STRUCTURAL, "Split a module into two"),
    "merge_services": (MutationCategory.STRUCTURAL, MutationClass.STRUCTURAL, "Merge two services into one"),
    "extract_interface": (MutationCategory.STRUCTURAL, MutationClass.STRUCTURAL, "Extract an interface from a service"),
    "replace_auth_strategy": (MutationCategory.SECURITY, MutationClass.STRATEGIC, "Replace authentication strategy"),
    "introduce_event_bus": (MutationCategory.TOPOLOGICAL, MutationClass.TOPOLOGICAL, "Introduce event-driven communication"),
    "introduce_cache": (MutationCategory.PERFORMANCE, MutationClass.ADDITIVE, "Add caching layer"),
    "add_read_replica": (MutationCategory.SCALABILITY, MutationClass.ADDITIVE, "Add database read replica"),
    "enable_cqrs": (MutationCategory.STRATEGIC, MutationClass.STRATEGIC, "Enable CQRS pattern"),
    "convert_sync_to_async": (MutationCategory.TOPOLOGICAL, MutationClass.TOPOLOGICAL, "Convert synchronous call to async event"),
    "add_rate_limiting": (MutationCategory.SECURITY, MutationClass.ADDITIVE, "Add rate limiting"),
    "add_audit_logging": (MutationCategory.SECURITY, MutationClass.ADDITIVE, "Add audit logging"),
    "add_circuit_breaker": (MutationCategory.RELIABILITY, MutationClass.ADDITIVE, "Add circuit breaker pattern"),
    "change_scaling_policy": (MutationCategory.SCALABILITY, MutationClass.PARAMETRIC, "Modify scaling parameters"),
    "adjust_ttl": (MutationCategory.PERFORMANCE, MutationClass.PARAMETRIC, "Adjust cache/session TTL"),
    "add_health_check": (MutationCategory.OPERATIONAL, MutationClass.ADDITIVE, "Add health check endpoint"),
    "introduce_event_sourcing": (MutationCategory.STRATEGIC, MutationClass.STRATEGIC, "Enable event sourcing"),
}
