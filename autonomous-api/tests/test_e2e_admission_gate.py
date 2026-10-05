from types import SimpleNamespace
import pytest
from app.engine.evolution_transaction import execute_evolution_transaction

# Static source-level contract test: admission must be gated after E2E verification.
def test_e2e_certification_gate_is_present():
    import inspect
    src=inspect.getsource(execute_evolution_transaction)
    assert 'transaction-e2e-verification-failed' in src
    assert 'transaction-e2e-verification-missing-evidence' in src
    assert src.index('transaction-e2e-verification-failed') < src.index('admit_successor')
