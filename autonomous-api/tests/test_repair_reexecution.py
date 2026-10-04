import pytest
from app.engine.repair_reexecution import reexecute_repaired_candidate


def test_repaired_candidate_requires_dependency_context():
    with pytest.raises(AttributeError):
        reexecute_repaired_candidate(
            None, None, dependency_graph={}, dependent_specs=(),
            verifiers={}, observations={}, evidence_by_property={},
            successor_architecture_id="s",
        )
