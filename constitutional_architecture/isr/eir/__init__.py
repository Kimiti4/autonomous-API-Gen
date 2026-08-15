"""
Evolution Intermediate Representation (EIR).

The EIR describes architectural CHANGE. The ISR describes state;
the EIR describes transitions between states.
"""

from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.eir.taxonomy import MutationCategory, MutationClass

__all__ = ["EIR", "Transformation", "MutationCategory", "MutationClass"]
