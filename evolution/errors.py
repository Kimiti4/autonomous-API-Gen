"""
Self-Evolution Engine error model.
"""


class EvolutionError(Exception):
    """Base evolution error."""


class ProposalNotFoundError(EvolutionError):
    """Raised when an evolution proposal is not found."""


class InvalidStateError(EvolutionError):
    """Raised when an operation is not valid for the current proposal state."""


class MutationError(EvolutionError):
    """Raised when mutation execution fails."""


class GovernanceDeniedError(EvolutionError):
    """Raised when governance denies evolution."""
