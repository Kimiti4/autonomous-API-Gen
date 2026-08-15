"""
Intermediate Requirement Representation (IRR).

The IRR captures intent. It is stable across architectural evolution.
Requirements and architecture evolve independently.
"""

from constitutional_architecture.isr.irr.model import IRR, Requirement, RequirementType

__all__ = ["IRR", "Requirement", "RequirementType"]
