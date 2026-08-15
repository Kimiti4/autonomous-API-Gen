"""
EIR — Evolution Intermediate Representation

The ISR describes state. The EIR describes transitions. Separating what
the architecture *is* from how it *changes* provides:
- Reversible transformations
- Mutation replay
- Learning which transformations consistently improve fitness
- Semantic architectural diffs
- Explainable evolution
"""

from constitutional_architecture.eir.transformation import (
    EIR, Transformation, MutationOperator, TransformationClass,
    create_split_module_operator, create_introduce_cache_operator,
    create_add_rate_limiting_operator, create_convert_to_async_operator,
    create_extract_interface_operator, create_add_audit_logging_operator,
    create_change_scaling_policy_operator, create_add_event_operator,
    create_merge_services_operator, create_add_circuit_breaker_operator,
    register_default_operators, get_operator_registry,
)

__all__ = [
    "EIR", "Transformation", "MutationOperator", "TransformationClass",
    "create_split_module_operator", "create_introduce_cache_operator",
    "create_add_rate_limiting_operator", "create_convert_to_async_operator",
    "create_extract_interface_operator", "create_add_audit_logging_operator",
    "create_change_scaling_policy_operator", "create_add_event_operator",
    "create_merge_services_operator", "create_add_circuit_breaker_operator",
    "register_default_operators", "get_operator_registry",
]