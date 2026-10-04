"""Atomic entry point for the ESAP evolution transaction."""
from __future__ import annotations

from .evolution_transaction import EvolutionTransaction, execute_evolution_transaction
from .transaction_atomicity import AtomicTransactionResult, run_atomic_transaction


def execute_evolution_transaction_atomic(*args, **kwargs) -> AtomicTransactionResult[EvolutionTransaction]:
    """Run the existing evolution transaction with explicit COMMITTED/ABORTED semantics.

    The underlying transaction remains responsible for its full evidence/audit
    construction. An exception at any stage produces an ABORTED result and no
    partially constructed EvolutionTransaction is returned.
    """
    return run_atomic_transaction(
        lambda: execute_evolution_transaction(*args, **kwargs),
        stage="evolution-transaction",
    )
