"""Infrastructure adapters for the Autonomous Intelligence Runtime (Cap-D).

Local inference is deployment topology; the adapters below wrap the
existing LanguageModelProvider contract as an L2 IntelligenceProvider.
"""

from .local_model_provider import LocalModelProvider
from .local_topology import LocalEndpoint, LocalTopology

__all__ = ["LocalModelProvider", "LocalEndpoint", "LocalTopology"]
