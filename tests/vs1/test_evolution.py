"""VS-D13 tests T01-T55: bounded architecture evolution (synthetic only)."""
from __future__ import annotations

import unittest

from vertical_slice import evolution as EVO


def _artifact():
    return EVO.build_evidence()


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        from vertical_slice import implementation as IMPL
        identity = IMPL.frozen_input_identity()
        self.assertEqual(
            identity["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(
            IMPL.frozen_input_identity()["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        from vertical_slice import candidates as C
        self.assertEqual(C.select_candidate()["selected"], "vs1-candidate-a")

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
        self.assertEqual(EVO.load_real_decision()["decision"], "NO_CHANGE")

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
        real_style = copy.deepcopy(EVO.synthetic_authorization())
        real_style["authorization_mode"] = "REAL"
        with self.assertRaises(EVO.EvolutionNotAuthorized):
            EVO.generate_candidates(real_style)

    def test_t14_synthetic_marked(self):
        fixture = EVO.synthetic_authorization()
        self.assertEqual(fixture["authorization_mode"], "SYNTHETIC_TEST_ONLY")

    def test_t15_synthetic_not_real(self):
        import copy
        fixture = EVO.synthetic_authorization()
        EVO.validate_authorization(fixture)
        real_style = copy.deepcopy(fixture)
        real_style["authorization_mode"] = "REAL"
        with self.assertRaises(EVO.EvolutionNotAuthorized):
            EVO.validate_authorization(real_style)

    def test_t16_invalid_blocked(self):
        with self.assertRaises(EVO.EvolutionError):
            EVO.validate_authorization({"authorization_mode": "SYNTHETIC_TEST_ONLY"})


class ProvenanceChain(unittest.TestCase):
    def test_t17_valid_accepted(self):
        EVO.validate_authorization(EVO.synthetic_authorization())

    def test_t18_objective_provenance(self):
        fixture = EVO.synthetic_authorization()
        self.assertTrue(fixture["objective"]["evidence_basis"])
        self.assertTrue(fixture["objective"]["finding_refs"])
        self.assertTrue(fixture["objective"]["hypothesis_refs"])

    def test_t19_finding_provenance(self):
        fixture = EVO.synthetic_authorization()
        self.assertTrue(fixture["finding_refs"])
        self.assertTrue(fixture["hypothesis_refs"])

    def test_t20_hypothesis_provenance(self):
        fixture = EVO.synthetic_authorization()
        self.assertEqual(fixture["hypothesis_refs"],
                         ["vs1-hypothesis-auth-model-adequate"])

    def test_t21_evidence_provenance(self):
        import json
        d10 = json.load(open("vertical_slice/evidence_acquisition_results.json"))
        self.assertEqual(len(d10["observations"]), 7)
        for record in d10["observations"]:
            self.assertIn("vs-d01-graph-sha256", record["provenance"])


class Lineage(unittest.TestCase):
    def test_t22_base_lineage(self):
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            self.assertEqual(candidate["parent_candidate_id"], "vs1-candidate-a")
            self.assertEqual(candidate["base_architecture_id"], "vs1-candidate-a")

    def test_t23_parent_valid(self):
        from vertical_slice import candidates as C
        self.assertEqual(C.select_candidate()["selected"], "vs1-candidate-a")
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            self.assertEqual(candidate["lineage"]["parent_candidate_id"],
                             "vs1-candidate-a")

    def test_t24_isr_refs(self):
        from vertical_slice.isr import build_task_tracker_isr
        isr_ids = set(build_task_tracker_isr().graph.nodes)
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            for ref in candidate["affected_isr_refs"]:
                self.assertIn(ref, isr_ids, (candidate["candidate_id"], ref))

    def test_t25_requirements_preserved(self):
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            blob = str(candidate).lower()
            for cap in ("cap-task-create", "cap-authentication"):
                self.assertIn(cap, blob, candidate["candidate_id"])

    def test_t26_allowed_scope(self):
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            changed = " ".join(candidate["changed_surfaces"]).lower()
            self.assertTrue("polic" in changed or "guard" in changed or
                            "entry" in changed, candidate["candidate_id"])

    def test_t27_forbidden_scope(self):
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            blob = str(candidate).lower()
            for marker in ("change the isr", "delete security",
                           "weaken authentication", "change persistence model"):
                self.assertNotIn(marker, blob, (candidate["candidate_id"], marker))

    def test_t28_invariants(self):
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            self.assertIn("CRUD lifecycle semantics",
                          candidate["preserved_invariants"])


class Generation(unittest.TestCase):
    def test_t29_candidate_a(self):
        artifact = _artifact()
        profiles = {c["profile"] for c in artifact["candidates"]}
        self.assertIn("central-policy", profiles)

    def test_t30_candidate_b(self):
        artifact = _artifact()
        profiles = {c["profile"] for c in artifact["candidates"]}
        self.assertIn("service-owned", profiles)

    def test_t31_candidate_c(self):
        artifact = _artifact()
        profiles = {c["profile"] for c in artifact["candidates"]}
        self.assertIn("policy-capability", profiles)

    def test_t32_distinct(self):
        import hashlib
        import json
        artifact = _artifact()
        digests = set()
        for candidate in artifact["candidates"]:
            normalized = json.dumps(
                {k: v for k, v in candidate.items()
                 if k not in ("candidate_id", "content_hash", "lineage_hash")},
                sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            self.assertNotIn(digest, digests, candidate["candidate_id"])
            digests.add(digest)
        self.assertEqual(len(digests), 3)

    def test_t33_duplicates_rejected(self):
        artifact = _artifact()
        doubled = artifact["candidates"] + [dict(artifact["candidates"][0])]
        with self.assertRaises(EVO.EvolutionError):
            EVO.check_distinct(doubled)

    def test_t34_inadmissible_rejected(self):
        import copy
        artifact = _artifact()
        bad = copy.deepcopy(artifact["candidates"][0])
        bad["affected_isr_refs"] = ["cap-no-such-thing"]
        admissible, reasons = EVO.check_admissible(bad)
        self.assertFalse(admissible)
        self.assertTrue(reasons)


class Determinism(unittest.TestCase):
    def test_t35_fitness_deterministic(self):
        first = EVO.fitness_candidate("central-policy")
        second = EVO.fitness_candidate("central-policy")
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["total"], 0.695)

    def test_t36_order_deterministic(self):
        first = EVO.order_candidates(_artifact()["candidates"])
        second = EVO.order_candidates(_artifact()["candidates"])
        self.assertEqual(first, second)
        self.assertEqual(first["order_kind"], "NON-AUTHORITATIVE_CANDIDATE_ORDER")

    def test_t37_same_seed(self):
        first = EVO.generate_candidates(EVO.synthetic_authorization(), seed=42)
        second = EVO.generate_candidates(EVO.synthetic_authorization(), seed=42)
        self.assertEqual(
            [c["content_hash"] for c in first],
            [c["content_hash"] for c in second])

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
        first = EVO.generate_candidates(EVO.synthetic_authorization(), seed=42)
        second = EVO.generate_candidates(EVO.synthetic_authorization(), seed=99)
        self.assertEqual(
            [c["content_hash"] for c in first],
            [c["content_hash"] for c in second])

    def test_t39_non_authoritative(self):
        ordering = EVO.order_candidates(_artifact()["candidates"])
        self.assertEqual(ordering["order_kind"], "NON-AUTHORITATIVE_CANDIDATE_ORDER")
        self.assertNotIn("selected_candidate", ordering)

    def test_t40_no_production_selection(self):
        artifact = _artifact()
        self.assertEqual(artifact["production_selection"], "NOT_PERFORMED")
        self.assertNotIn("selected_candidate", artifact)


class Firewalls(unittest.TestCase):
    def _identifiers(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evolution.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        return identifiers, src

    def test_t41_isr(self):
        identifiers, _src = self._identifiers()
        for token in ("mutate", "crossover", "rewrite", "retire", "migrate", "patch"):
            self.assertNotIn(token, identifiers, token)

    def test_t42_requirements(self):
        _identifiers, src = self._identifiers()
        lowered = src.lower()
        for marker in ("new requirement", "rewrite requirement", "change the isr"):
            self.assertNotIn(marker, lowered, marker)

    def test_t43_d12(self):
        import json
        before = open("vertical_slice/evolution_decision_v2_evidence.json",
                      encoding="utf-8").read()
        _artifact()
        after = open("vertical_slice/evolution_decision_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)
        json.loads(after)

    def test_t44_d11(self):
        import json
        before = open("vertical_slice/interpretation_v2_evidence.json",
                      encoding="utf-8").read()
        _artifact()
        after = open("vertical_slice/interpretation_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t45_d10(self):
        import json
        before = open("vertical_slice/evidence_acquisition_results.json",
                      encoding="utf-8").read()
        _artifact()
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
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            admissible, reasons = EVO.check_admissible(candidate)
            self.assertTrue(admissible, (candidate["candidate_id"], reasons))
            self.assertIn("sec-credential-safety", candidate["affected_isr_refs"])
            self.assertIn("sec-tenant-isolation", candidate["affected_isr_refs"])

    def test_t50_secrets(self):
        import json
        import re
        blob = json.dumps(_artifact()).lower()
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob))
        for marker in ("alice-secret-pw", "bob-secret-pw", "cara-secret-pw",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "vs1-d10-token"):
            self.assertNotIn(marker, blob, marker)

    def test_t51_malformed_isr(self):
        import copy
        artifact = _artifact()
        bad = copy.deepcopy(artifact["candidates"][0])
        bad["affected_isr_refs"] = ["cap-no-such-thing"]
        admissible, reasons = EVO.check_admissible(bad)
        self.assertFalse(admissible)
        self.assertTrue(any("ISR reference" in r or "unknown ISR" in r
                            for r in reasons))

    def test_t52_missing_provenance(self):
        import copy
        artifact = _artifact()
        bad = copy.deepcopy(artifact["candidates"][0])
        del bad["lineage"]
        admissible, reasons = EVO.check_admissible(bad)
        # lineage absent from the record entirely: fail closed via KeyError-free check
        self.assertFalse(admissible or "lineage" in bad)

    def test_t53_forbidden_surface(self):
        fixture = EVO.synthetic_authorization()
        self.assertIn("changing the ISR", fixture["forbidden_change_surface"])
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            self.assertNotIn("changing the ISR", candidate["changed_surfaces"])

    def test_t54_hash(self):
        import hashlib
        import json
        artifact = _artifact()
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in artifact.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(artifact["content_hash"], recomputed)

    def test_t55_lineage_hash(self):
        import hashlib
        artifact = _artifact()
        for candidate in artifact["candidates"]:
            recomputed = hashlib.sha256("|".join([
                candidate["parent_candidate_id"],
                __import__("json").dumps(
                    candidate["architecture_delta"], sort_keys=True),
                candidate["objective_id"]]).encode()).hexdigest()
            self.assertEqual(candidate["lineage_hash"], recomputed)


if __name__ == "__main__":
    unittest.main()
