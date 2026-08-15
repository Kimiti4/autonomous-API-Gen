"""
Backend context helpers.

Helper utilities for backends to extract information from a
CompilationContext.
"""

from __future__ import annotations

from typing import Any

from ..models import CompilationContext


def get_isr_field(context: CompilationContext, field: str, default: Any = None) -> Any:
    """Get a top-level field from the ISR payload."""
    return context.isr.get(field, default)


def get_isr_id(context: CompilationContext) -> str:
    """Get the ISR ID from compilation context."""
    return str(context.isr.get("isr_id", ""))


def get_isr_version(context: CompilationContext) -> str:
    """Get the ISR version from compilation context."""
    return str(context.isr.get("version", ""))


def get_isr_name(context: CompilationContext) -> str:
    """Get the ISR system name from compilation context."""
    return str(context.isr.get("name", ""))


def get_isr_domains(context: CompilationContext) -> list[dict[str, Any]]:
    """Get domains from the ISR payload."""
    domains = context.isr.get("domains", [])

    if not isinstance(domains, list):
        return []

    return domains


def get_plan_parameter(
    context: CompilationContext,
    key: str,
    default: Any = None,
) -> Any:
    """Get a compilation plan parameter."""
    return context.plan.parameters.get(key, default)


def output_directory(context: CompilationContext) -> str:
    """Get the output directory from compilation context."""
    return context.output_directory