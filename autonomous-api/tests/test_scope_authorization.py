import pytest

from app.engine.generation_scope import GenerationScope, validate_scope
from app.engine.scope_authorization import (
    MutationIntent,
    ScopeViolation,
    authorize_mutation,
    authorize_mutations,
    authorize_scope_mutations,
)


def test_frontend_scope_allows_frontend_mutation():
    contract = validate_scope(GenerationScope.FRONTEND_ONLY)
    authorize_mutation(contract, MutationIntent("frontend", "edit", "src/App.tsx"))


def test_frontend_scope_blocks_backend_mutation():
    contract = validate_scope(GenerationScope.FRONTEND_ONLY)
    with pytest.raises(ScopeViolation, match="scope-violation"):
        authorize_mutation(contract, MutationIntent("backend", "edit", "api/app.py"))


def test_backend_scope_blocks_api_contract_mutation():
    contract = validate_scope(GenerationScope.BACKEND_ONLY)
    with pytest.raises(ScopeViolation):
        authorize_mutation(contract, MutationIntent("api_contract", "edit", "openapi.yaml"))


def test_api_contract_scope_allows_only_api_contract():
    contract = validate_scope(GenerationScope.API_CONTRACT_ONLY)
    authorize_mutation(contract, MutationIntent("api_contract", "edit", "openapi.yaml"))
    with pytest.raises(ScopeViolation):
        authorize_mutation(contract, MutationIntent("frontend", "edit", "src/App.tsx"))


def test_batch_authorization_fails_before_returning_partial_set():
    contract = validate_scope(GenerationScope.FRONTEND_ONLY)
    mutations = (
        MutationIntent("frontend", "edit", "src/App.tsx"),
        MutationIntent("backend", "edit", "api/app.py"),
    )
    with pytest.raises(ScopeViolation):
        authorize_mutations(contract, mutations)


def test_full_application_allows_all_supported_surfaces():
    contract = validate_scope(GenerationScope.FULL_APPLICATION)
    authorize_mutations(
        contract,
        (
            MutationIntent("frontend", "edit", "src/App.tsx"),
            MutationIntent("backend", "edit", "api/app.py"),
            MutationIntent("api_contract", "edit", "openapi.yaml"),
        ),
    )


def test_unknown_surface_fails_closed():
    contract = validate_scope(GenerationScope.FULL_APPLICATION)
    with pytest.raises(ValueError, match="unknown-software-surface"):
        authorize_mutation(contract, MutationIntent("database", "edit", "db.sql"))


def test_missing_mutation_identity_fails_closed():
    with pytest.raises(ValueError, match="missing-mutation-target"):
        MutationIntent("frontend", "edit", "")
