import pytest

from app.engine.generation_scope import GenerationScope, validate_scope


@pytest.mark.parametrize(
    "scope,allowed,blocked",
    [
        (GenerationScope.FULL_APPLICATION, ("frontend","backend","api_contract"), ()),
        (GenerationScope.FRONTEND_ONLY, ("frontend",), ("backend","api_contract")),
        (GenerationScope.BACKEND_ONLY, ("backend",), ("frontend","api_contract")),
        (GenerationScope.API_CONTRACT_ONLY, ("api_contract",), ("frontend","backend")),
    ],
)
def test_scope_contract_is_explicit(scope, allowed, blocked):
    contract = validate_scope(scope)
    for surface in allowed:
        assert contract.allows(surface)
    for surface in blocked:
        assert not contract.allows(surface)


def test_unknown_surface_fails_closed():
    contract = validate_scope(GenerationScope.FRONTEND_ONLY)
    with pytest.raises(ValueError, match="unknown-software-surface"):
        contract.allows("database")


def test_invalid_scope_fails_closed():
    with pytest.raises(ValueError, match="invalid-generation-scope"):
        validate_scope("frontend-only")


def test_full_application_allows_all_surfaces():
    contract = validate_scope(GenerationScope.FULL_APPLICATION)
    assert contract.allows("frontend")
    assert contract.allows("backend")
    assert contract.allows("api_contract")
