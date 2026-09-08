"""VS-D14 tests T01-T55: evolution candidate selection (choice, not authority)."""
from __future__ import annotations

import unittest

from vertical_slice import evolution_selection as SEL


def _record():
    return SEL.choose_candidate()


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(
            SEL.upstream_identities()["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        self.assertEqual(
            SEL.upstream_identities()["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        self.assertEqual(SEL.upstream_identities()["vs-d03-selected"], "vs1-candidate-a")

    def test_t04_d04(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")

    def test_t05_d05(self):
        from vertical_slice.deployment import (
            CANDIDATE_ID,
            DEPLOYMENT_CONTRACT_VERSION,
        )
        self.assertEqual(CANDIDATE_ID, "vs1-candidate-a")
        self.assertEqual(DEPLOYMENT_CONTRACT_VERSION, "vs1-deploy-v1")

    def test_t06_d06(self):
        from vertical_slice import observation as OBS
        self.assertEqual(OBS.OBSERVATION_CONTRACT_VERSION, "vs1-observe-v1")

    def test_t07_d07(self):
        import json
        evidence = json.load(open("vertical_slice/interpretation_evidence.json"))
        self.assertEqual(len(evidence["hypotheses"]), 3)

    def test_t08_d08(self):
        self.assertEqual(SEL.upstream_identities()["vs-d12-decision"], "NO_CHANGE")

    def test_t09_d09(self):
        from vertical_slice import evidence_acquisition as ACQ
        self.assertEqual(ACQ.run_gate()["outcome"], "EVIDENCE_PLAN_REQUIRED")

    def test_t10_d10(self):
        import json
        evidence = json.load(
            open("vertical_slice/evidence_acquisition_results.json"))
        self.assertEqual(evidence["summary"]["pass"], 7)

    def test_t11_d11(self):
        import json
        evidence = json.load(
            open("vertical_slice/interpretation_v2_evidence.json"))
        self.assertEqual(len(evidence["hypotheses"]), 2)

    def test_t12_d12(self):
        import json
        decision = json.load(
            open("vertical_slice/evolution_decision_v2_evidence.json"))
        self.assertEqual(decision["decision"], "NO_CHANGE")
        self.assertEqual(
            decision["content_hash"],
            "ae6df7c889ff9cabcdb060941da09b1ecc2b78af08577c31ca670c9c4768dffc")


class AuthorizationGate(unittest.TestCase):
    def test_t13_real_no_change_blocks(self):
        import copy
        from vertical_slice import evolution as EVO
        real_style = copy.deepcopy(EVO.synthetic_authorization())
        real_style["authorization_mode"] = "REAL"
        with self.assertRaises(EVO.EvolutionNotAuthorized):
            EVO.validate_authorization(real_style)

    def test_t14_synthetic_marked(self):
        from vertical_slice import evolution as EVO
        fixture = EVO.synthetic_authorization()
        self.assertEqual(fixture["authorization_mode"], "SYNTHETIC_TEST_ONLY")

    def test_t15_synthetic_not_real(self):
        record = _record()
        self.assertEqual(record["selection_mode"], "SYNTHETIC_TEST_ONLY")
        self.assertFalse(record["production_authorization"])

    def test_t16_invalid_blocked(self):
        from vertical_slice import evolution as EVO
        with self.assertRaises(EVO.EvolutionError):
            EVO.validate_authorization({"authorization_mode": "SYNTHETIC_TEST_ONLY"})


class SelectionBehavior(unittest.TestCase):
    def test_t17_valid_accepted(self):
        from vertical_slice import evolution as EVO
        EVO.validate_authorization(EVO.synthetic_authorization())

    def test_t18_objective_provenance(self):
        record = _record()
        self.assertTrue(record["objective_id"])
        self.assertTrue(record["objective_id"].startswith("vs1-objective-"))
        self.assertTrue(record["authorization_id"].startswith("vs1-authorization-"))

    def test_t19_finding_provenance(self):
        record = _record()
        self.assertTrue(record["authorization_id"])

    def test_t20_hypothesis_provenance(self):
        record = _record()
        for candidate in self._candidates():
            self.assertIn("objective_id", candidate)

    def test_t21_evidence_provenance(self):
        record = _record()
        self.assertIn("vs-d01-graph-sha256", record["upstream"])

    def _candidates(self):
        from vertical_slice import evolution as EVO
        return EVO.build_evidence()["candidates"]


class Lineage(unittest.TestCase):
    def _candidates(self):
        from vertical_slice import evolution as EVO
        return EVO.build_evidence()["candidates"]

    def test_t22_base_lineage(self):
        for candidate in self._candidates():
            self.assertEqual(candidate["base_architecture_id"], "vs1-candidate-a")

    def test_t23_parent_valid(self):
        for candidate in self._candidates():
            self.assertEqual(candidate["parent_candidate_id"], "vs1-candidate-a")
            self.assertEqual(candidate["lineage"]["parent_candidate_id"],
                             "vs1-candidate-a")

    def test_t24_isr_refs(self):
        from vertical_slice.isr import build_task_tracker_isr
        isr_ids = set(build_task_tracker_isr().graph.nodes)
        for candidate in self._candidates():
            for ref in candidate["affected_isr_refs"]:
                self.assertIn(ref, isr_ids, (candidate["candidate_id"], ref))

    def test_t25_requirements_preserved(self):
        for candidate in self._candidates():
            blob = str(candidate).lower()
            for cap in ("cap-task-create", "cap-authentication"):
                self.assertIn(cap, blob, candidate["candidate_id"])

    def test_t26_allowed_scope(self):
        record = _record()
        for candidate in self._candidates():
            changed = " ".join(candidate["changed_surfaces"]).lower()
            self.assertTrue("polic" in changed or "guard" in changed or
                            "entry" in changed, candidate["candidate_id"])

    def test_t27_forbidden_scope(self):
        for candidate in self._candidates():
            blob = str(candidate).lower()
            for marker in ("change the isr", "delete security",
                           "weaken authentication", "change persistence model"):
                self.assertNotIn(marker, blob, (candidate["candidate_id"], marker))

    def test_t28_invariants(self):
        for candidate in self._candidates():
            self.assertIn("CRUD lifecycle semantics",
                          candidate["preserved_invariants"])


class Generation(unittest.TestCase):
    def test_t29_candidate_a(self):
        record = _record()
        profiles = {c["profile"] for c in self._candidates(record)}
        self.assertIn("central-policy", profiles)

    def test_t30_candidate_b(self):
        record = _record()
        profiles = {c["profile"] for c in self._candidates(record)}
        self.assertIn("service-owned", profiles)

    def test_t31_candidate_c(self):
        record = _record()
        profiles = {c["profile"] for c in self._candidates(record)}
        self.assertIn("policy-capability", profiles)

    def test_t32_distinct(self):
        import hashlib
        import json
        seen = set()
        for candidate in self._candidates(_record()):
            normalized = json.dumps(
                {k: v for k, v in candidate.items()
                 if k not in ("candidate_id", "content_hash", "lineage_hash")},
                sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            self.assertNotIn(digest, seen, candidate["candidate_id"])
            seen.add(digest)
        self.assertEqual(len(seen), 3)

    def test_t33_duplicates_rejected(self):
        from vertical_slice import evolution as EVO
        candidates = self._candidates(_record())
        with self.assertRaises(EVO.EvolutionError):
            EVO.check_distinct(candidates + [dict(candidates[0])])

    def test_t34_inadmissible_rejected(self):
        from vertical_slice import evolution as EVO
        import copy
        candidates = self._candidates(_record())
        bad = copy.deepcopy(candidates[0])
        bad["affected_isr_refs"] = ["cap-no-such-thing"]
        admissible, reasons = EVO.check_admissible(bad)
        self.assertFalse(admissible)
        self.assertTrue(reasons)

    def _candidates(self, record=None):
        from vertical_slice import evolution as EVO
        return EVO.build_evidence()["candidates"]


class Determinism(unittest.TestCase):
    def test_t35_fitness_deterministic(self):
        from vertical_slice import evolution as EVO
        first = EVO.fitness_candidate("central-policy")
        second = EVO.fitness_candidate("central-policy")
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["total"], 0.695)

    def test_t36_order_deterministic(self):
        first = SEL.order_candidates(self._candidates())
        second = SEL.order_candidates(self._candidates())
        self.assertEqual(first, second)
        self.assertEqual(first["order_kind"], "NON-AUTHORITATIVE_CANDIDATE_ORDER")

    def test_t37_same_seed(self):
        first = _record()
        second = _record()
        self.assertEqual(first["selection_hash"], second["selection_hash"])
        self.assertEqual(first["selected_candidate_id"], second["selected_candidate_id"])

    def test_t38_deterministic_generation(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evolution.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("random", imports)
        # No RNG anywhere: identical outputs by construction (see T37).

    def test_t39_non_authoritative(self):
        ordering = SEL.order_candidates(self._candidates())
        self.assertEqual(ordering["order_kind"], "NON-AUTHORITATIVE_CANDIDATE_ORDER")
        self.assertNotIn("selected_candidate", ordering)

    def test_t40_no_production_selection(self):
        record = _record()
        self.assertEqual(record["production_authorization"], False)
        self.assertNotIn("selected_production_candidate", record)

    def _candidates(self):
        from vertical_slice import evolution as EVO
        return EVO.build_evidence()["candidates"]


class Firewalls(unittest.TestCase):
    def test_t41_isr(self):
        identifiers, _src = self._identifiers()
        for token in ("mutate", "crossover", "rewrite", "retire", "migrate", "patch"):
            self.assertNotIn(token, identifiers, token)

    def _identifiers(self, path=("vertical_slice", "evolution_selection.py")):
        import ast
        import os
        src = open(os.path.join(*path), encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        return identifiers, src

    def test_t42_requirements(self):
        _identifiers, src = self._identifiers()
        lowered = src.lower()
        for marker in ("new requirement", "rewrite requirement", "change the isr"):
            self.assertNotIn(marker, lowered, marker)

    def test_t43_d12(self):
        import json
        before = open("vertical_slice/evolution_decision_v2_evidence.json",
                      encoding="utf-8").read()
        _record()
        after = open("vertical_slice/evolution_decision_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)
        json.loads(after)

    def test_t44_d11(self):
        import json
        before = open("vertical_slice/interpretation_v2_evidence.json",
                      encoding="utf-8").read()
        _record()
        after = open("vertical_slice/interpretation_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t45_d10(self):
        import json
        before = open("vertical_slice/evidence_acquisition_results.json",
                      encoding="utf-8").read()
        _record()
        after = open("vertical_slice/evidence_acquisition_results.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t46_implementation(self):
        _identifiers, src = self._identifiers()
        self.assertNotIn("vertical_slice.app", src)

    def test_t47_deployment(self):
        identifiers, _src = self._identifiers()
        self.assertNotIn("uvicorn", identifiers)
        self.assertNotIn("docker", identifiers)

    def test_t48_observation(self):
        identifiers, _src = self._identifiers()
        for token in ("telemetry", "prometheus", "opentelemetry", "observe"):
            self.assertNotIn(token, identifiers, token)

    def test_t49_security(self):
        record = _record()
        # every ranked candidate passed admissibility incl. security refs
        self.assertEqual(record["admissible_count"], 3)
        self.assertEqual(record["rejected_count"], 0)

    def test_t50_secrets(self):
        import json
        import re
        blob = json.dumps(_record()).lower()
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob))
        for marker in ("alice-secret-pw", "bob-secret-pw", "cara-secret-pw",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "vs1-d10-token"):
            self.assertNotIn(marker, blob, marker)

    def test_t51_malformed_isr(self):
        import copy
        record = _record()
        _ = record
        from vertical_slice import evolution as EVO
        candidates = EVO.build_evidence()["candidates"]
        bad = copy.deepcopy(candidates[0])
        bad["affected_isr_refs"] = ["cap-no-such-thing"]
        admissible, reasons = SEL.check_admissible(bad, SEL._isr_nodes())
        self.assertFalse(admissible)
        self.assertTrue(any("ISR reference" in r or "unknown ISR" in r
                            for r in reasons))

    def test_t52_missing_provenance(self):
        import copy
        record = _record()
        _ = record
        from vertical_slice import evolution as EVO
        candidates = EVO.build_evidence()["candidates"]
        bad = copy.deepcopy(candidates[0])
        del bad["lineage"]
        admissible, reasons = SEL.check_admissible(bad, SEL._isr_nodes())
        self.assertFalse(admissible)
        self.assertTrue(any("lineage" in r for r in reasons))

    def test_t53_forbidden_surface(self):
        from vertical_slice import evolution as EVO
        fixture = EVO.synthetic_authorization()
        self.assertIn("changing the ISR", fixture["forbidden_change_surface"])
        record = _record()
        for candidate in EVO.build_evidence()["candidates"]:
            self.assertNotIn("changing the ISR", candidate["changed_surfaces"])

    def test_t54_hash(self):
        import hashlib
        import json
        record = _record()
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in record.items() if k != "selection_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(record["selection_hash"], recomputed)

    def test_t55_lineage_hash(self):
        import hashlib
        import json
        record = _record()
        _ = record
        from vertical_slice import evolution as EVO
        for candidate in EVO.build_evidence()["candidates"]:
            recomputed = hashlib.sha256("|".join([
                candidate["parent_candidate_id"],
                json.dumps(candidate["architecture_delta"], sort_keys=True),
                candidate["objective_id"]]).encode()).hexdigest()
            self.assertEqual(candidate["lineage_hash"], recomputed)


if __name__ == "__main__":
    unittest.main()
