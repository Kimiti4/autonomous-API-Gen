from certification.campaign.verify_campaign import _semantic_correspondence_problem


def test_certification_rejects_missing_semantic_correspondence():
    assert "missing source-bound" in _semantic_correspondence_problem({
        "trial_id": "trial-1", "verdict": "CERTIFIED", "repo_hash": "abc"
    })


def test_certification_rejects_failed_semantic_correspondence():
    problem = _semantic_correspondence_problem({
        "semantic_correspondence": {
            "passed": False, "source_hash": "s", "mapping_hash": "m", "candidate_hash": "c"
        },
        "repo_hash": "c",
    })
    assert problem == "source-bound semantic correspondence did not pass"


def test_certification_rejects_candidate_hash_mismatch():
    problem = _semantic_correspondence_problem({
        "semantic_correspondence": {
            "passed": True, "source_hash": "s", "mapping_hash": "m", "candidate_hash": "old"
        },
        "repo_hash": "new",
    })
    assert problem == "semantic correspondence candidate hash does not match certified repository hash"


def test_certification_accepts_complete_candidate_bound_semantic_evidence():
    assert _semantic_correspondence_problem({
        "semantic_correspondence": {
            "passed": True, "source_hash": "source-v1", "mapping_hash": "mapping-v1",
            "candidate_hash": "candidate-v1",
        },
        "repo_hash": "candidate-v1",
    }) is None


def test_certification_rejects_missing_hashes():
    problem = _semantic_correspondence_problem({
        "semantic_correspondence": {
            "passed": True, "source_hash": "source-v1", "mapping_hash": "",
            "candidate_hash": "candidate-v1",
        },
        "repo_hash": "candidate-v1",
    })
    assert problem == "semantic correspondence missing mapping_hash"
