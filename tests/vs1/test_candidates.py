"""VS-D03 tests: deterministic candidate generation + selection (T01-T12)."""
from __future__ import annotations

import unittest

from vertical_slice import candidates as C
from vertical_slice.isr import build_task_tracker_isr
from vertical_slice.requirements import build_task_tracker_requirements


class TestT01FailClosed(unittest.TestCase):
    def test_unknown_requirement_breaks_lineage(self):
        from dataclasses import replace
        cands = C.build_candidates()
        bad = replace(cands[0], requirement_coverage=("req-no-such-thing",))
        self.assertFalse(C.check_admissible(bad)["A1-requirement-lineage"])

    def test_unknown_isr_breaks_lineage(self):
        from dataclasses import replace
        cands = C.build_candidates()
        bad = replace(cands[0], isr_coverage=("cap-no-such-thing",))
        self.assertFalse(C.check_admissible(bad)["A2-isr-lineage"])

    def test_missing_mandatory_capability_rejected(self):
        from dataclasses import replace
        cands = C.build_candidates()
        bad = replace(cands[0], isr_coverage=("svc-identity",))
        self.assertFalse(C.check_admissible(bad)["A3-capabilities"])


class TestT02Count(unittest.TestCase):
    def test_declared_set(self):
        self.assertEqual(len(C.build_candidates()), 2)


class TestT03Identity(unittest.TestCase):
    def test_ids_stable_unique(self):
        first = [c.candidate_id for c in C.build_candidates()]
        second = [c.candidate_id for c in C.build_candidates()]
        self.assertEqual(first, second)
        self.assertEqual(len(set(first)), len(first))


class TestT04Determinism(unittest.TestCase):
    def test_repeated_generation_identical(self):
        self.assertEqual(C.build_candidates(), C.build_candidates())

    def test_repeated_scoring_identical(self):
        cands = C.build_candidates()
        ranked1 = C.rank_candidates(cands)
        ranked2 = C.rank_candidates(cands)
        self.assertEqual(
            [s for _, _, s in ranked1], [s for _, _, s in ranked2])


class TestT05Lineage(unittest.TestCase):
    def test_every_requirement_resolves(self):
        graph = build_task_tracker_requirements()
        for cand in C.build_candidates():
            for req_id in cand.requirement_coverage:
                self.assertIn(req_id, graph.nodes, (cand.candidate_id, req_id))

    def test_every_isr_ref_resolves(self):
        rev = build_task_tracker_isr()
        for cand in C.build_candidates():
            for isr_id in cand.isr_coverage:
                self.assertIn(isr_id, rev.graph.nodes, (cand.candidate_id, isr_id))


class TestT06Admissibility(unittest.TestCase):
    def test_all_declared_admissible(self):
        for cand in C.build_candidates():
            checks = C.check_admissible(cand)
            self.assertTrue(all(checks.values()), (cand.candidate_id, checks))

    def test_no_compensating_scores(self):
        from dataclasses import replace
        cands = C.build_candidates()
        bad = replace(cands[0], security_posture=())
        self.assertFalse(C.check_admissible(bad)["A4-security"])
        ranked_ids = [c.candidate_id for c, _, _ in C.rank_candidates(cands)]
        self.assertNotIn("tampered", ranked_ids)


class TestT07Scoring(unittest.TestCase):
    def test_scores_reproducible_and_bounded(self):
        cands = C.build_candidates()
        for cand in cands:
            first = C.score_candidate(cand, 5, 2)
            second = C.score_candidate(cand, 5, 2)
            self.assertEqual(first, second)
            for value in first.values():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_expected_winner_score(self):
        cands = C.build_candidates()
        ranked = C.rank_candidates(cands)
        self.assertEqual(ranked[0][0].candidate_id, "vs1-candidate-a")
        # A: 0.4*1.0 + 0.3*1.0 + 0.2*(1-1/3) + 0.1*(1-1/2) = 0.883333
        self.assertAlmostEqual(ranked[0][2]["total"], 0.883333)


class TestT08Ranking(unittest.TestCase):
    def test_ranking_deterministic(self):
        cands = C.build_candidates()
        first = [c.candidate_id for c, _, _ in C.rank_candidates(cands)]
        second = [c.candidate_id for c, _, _ in C.rank_candidates(tuple(reversed(cands)))]
        self.assertEqual(first, second)
        self.assertEqual(first, ["vs1-candidate-a", "vs1-candidate-b"])


class TestT09Ties(unittest.TestCase):
    def test_tie_fails_closed(self):
        from dataclasses import replace
        cands = C.build_candidates()
        # identical profiles including id: full tie on every tie-breaker
        twin = replace(cands[0], candidate_id=cands[0].candidate_id)
        decision = C.select_candidate((cands[0], twin))
        self.assertIsNone(decision["selected"])
        self.assertIn("TIE", decision["reason"])

    def test_no_admissible_yields_none(self):
        decision = C.select_candidate(())
        self.assertIsNone(decision["selected"])


class TestT10Selection(unittest.TestCase):
    def test_same_inputs_same_winner(self):
        first = C.select_candidate()
        second = C.select_candidate()
        self.assertEqual(first, second)
        self.assertEqual(first["selected"], "vs1-candidate-a")
        self.assertEqual(first["selection_policy_version"], C.SELECTION_POLICY_VERSION)

    def test_decision_carries_refs(self):
        decision = C.select_candidate()
        self.assertIn("req-task-create", decision["requirement_refs"])
        self.assertIn("cap-task-create", decision["isr_refs"])
        self.assertTrue(decision["decision_rationale"])
        self.assertTrue(decision["decision_provenance"])


class TestT11UpstreamImmutable(unittest.TestCase):
    def test_candidates_cannot_mutate_upstream(self):
        graph_before = build_task_tracker_requirements()
        rev_before = build_task_tracker_isr()
        C.select_candidate()
        self.assertEqual(build_task_tracker_requirements(), graph_before)
        self.assertEqual(build_task_tracker_isr(), rev_before)


class TestT12Boundary(unittest.TestCase):
    def test_no_implementation_side_effects(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "candidates.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertLessEqual(imports, {"__future__", "hashlib", "json",
                                       "dataclasses", "vertical_slice"},
                             imports)
        lowered = src.lower()
        for token in ("uvicorn", "docker", "telemetry"):
            self.assertNotIn(token, lowered, token)


if __name__ == "__main__":
    unittest.main()
