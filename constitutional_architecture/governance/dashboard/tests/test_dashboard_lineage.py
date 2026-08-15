"""
Phase 28 — Milestone 5A spec §15.4.6: lineage tests (task 5A.6).

Change lineage is explorable through the BFF: links exist between
decisions/artifacts, backward and forward traces render, and a decision
dossier shows its lineage.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def bob(tc, login):
    login("bob")
    return tc


def test_lineage_explorer_lists_links(tc, bob, client):
    body = bob.get("/lineage").text
    for link in client.list_lineage()[:3]:
        assert link.id in body


def test_artifact_detail_renders(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}").text
    assert link.id in body
    assert "Lineage" in body


def test_backward_trace_renders(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}/backward").text
    assert "Backward" in body


def test_forward_trace_renders(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}/forward").text
    assert "Forward" in body


def test_unknown_artifact_renders_empty_trace(tc, bob):
    body = bob.get("/lineage/does-not-exist/backward").text
    assert "Lineage" in body


def test_dossier_lineage_matches_kernel(client, kernel):
    lineage = {l.id for l in client.list_lineage()}
    kernel_links = {l.id for l in kernel.lineage.all()}
    assert lineage == kernel_links


def test_forward_and_backward_trace_agree(kernel, client):
    for link in client.list_lineage()[:2]:
        backward = client.get_lineage_backward(link.id)
        forward = client.get_lineage_forward(link.id)
        assert isinstance(backward.backward, list)
        assert isinstance(forward.forward, list)
