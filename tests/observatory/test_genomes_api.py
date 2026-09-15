"""Genome API tests: overview/detail contract over live TestClient."""
from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from tests.observatory.conftest import register_store_cleanup

WRITER = {"X-Actor-Id": "writer-1", "X-Actor-Role": "operator",
          "X-Observatory-Token": "test-token"}


def _client(testcase: unittest.TestCase):
    import observatory.backend.main as main_module

    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    os.environ["OBSERVATORY_DB_PATH"] = os.path.join(tmp.name, "obs.sqlite3")
    os.environ["OBSERVATORY_API_TOKEN"] = "test-token"
    main_module.get_settings.cache_clear()
    from observatory.backend.main import create_app
    client = TestClient(create_app())
    register_store_cleanup(testcase, client)
    return client


def _emit(client, **overrides):
    base = {"source": "test", "category": "evolution",
            "type": "genome_defined", "subject_id": "GEN-1",
            "payload": {"genome_id": "GEN-1",
                        "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
                        "generation": 1,
                        "objective": "Priority capability."}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class GenomesApi(unittest.TestCase):
    def test_overview_empty(self):
        client = _client(self)
        response = client.get("/observatory/genomes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_lifecycle_populates(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="gene_defined", subject_id="GENE-ENGINE",
              payload={"genome_id": "GEN-1", "gene_id": "GENE-ENGINE",
                       "chromosome": "Persistence", "value": "sqlite"})
        _emit(client, type="selection_recorded", subject_id="GEN-1",
              payload={"genome_id": "GEN-1",
                       "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
                       "outcome": "selected"})
        overview = client.get("/observatory/genomes").json()
        self.assertEqual(len(overview), 1)
        item = overview[0]
        self.assertEqual(item["status"], "selected")
        self.assertEqual(item["gene_count"], 1)
        self.assertEqual(item["selection_count"], 1)
        self.assertEqual(item["pareto_state"], "unknown")

    def test_detail_404(self):
        client = _client(self)
        missing = client.get("/observatory/genomes/GEN-nope")
        self.assertEqual(missing.status_code, 404)

    def test_detail_sections(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="gene_mutated", subject_id="GENE-ENGINE",
              payload={"genome_id": "GEN-1", "gene_id": "GENE-ENGINE",
                       "chromosome": "Persistence",
                       "previous_value": "sqlite",
                       "new_value": "postgresql",
                       "reason": "Durability review."})
        _emit(client, type="gene_crossover", subject_id="GENE-TRACE",
              payload={"genome_id": "GEN-1", "gene_id": "GENE-TRACE",
                       "chromosome": "Observability",
                       "parent_genome_ids": ["GEN-0", "GEN-1"]})
        detail = client.get("/observatory/genomes/GEN-1").json()
        self.assertEqual(len(detail["genes"]), 2)
        gene = next(gene for gene in detail["genes"]
                    if gene["gene_id"] == "GENE-ENGINE")
        self.assertEqual(gene["value"], "postgresql")
        self.assertEqual(gene["previous_value"], "sqlite")
        self.assertEqual(len(detail["mutations"]), 1)
        self.assertEqual(
            detail["mutations"][0]["new_value"], "postgresql")
        self.assertEqual(len(detail["crossovers"]), 1)
        self.assertEqual(detail["crossovers"][0]["parent_genome_ids"],
                         ["GEN-0", "GEN-1"])
        chromosomes = {c["name"]: c for c in detail["chromosomes"]}
        self.assertEqual(
            list(chromosomes),
            ["Persistence", "Observability"])
        self.assertEqual(detail["unknowns"], [])
        self.assertEqual(detail["contradictions"], [])

    def test_rejected_renders(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="genome_rejected",
              payload={"genome_id": "GEN-1"})
        overview = client.get("/observatory/genomes").json()
        self.assertEqual(overview[0]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
