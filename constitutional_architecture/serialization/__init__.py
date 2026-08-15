"""
Serialization — JSON ↔ In-Memory Graph Round-Trip

Provides lossless serialization and deserialization of ISR graphs
to/from JSON. The round-trip must preserve all architectural information
with zero loss.
"""

from constitutional_architecture.serialization.serializer import ISRSerializer
from constitutional_architecture.serialization.parser import ISRParser

__all__ = [
    "ISRSerializer", "ISRParser",
]