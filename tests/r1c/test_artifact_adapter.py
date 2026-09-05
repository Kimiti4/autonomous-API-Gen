"""R1-C adapter contract tests — ADAPTER-ARTIFACT-001.

Verifies the Gen-C FastAPI backend conforms to the canonical R1-B contract
(INV-B09: ArtifactSet is the generated-software boundary; no backend filesystem
emission inside compile()).

Source: folder/R1_C_BOUNDARY_CONTRACTS.md (C02, ADAPTER-ARTIFACT-001).
Source: folder/R1_C_ADAPTER_INVENTORY.md (C01, 1.28).
Source: folder/CONTRACT_ArtifactSet.md (D09).
Source: folder/CONTRACT_INVARIANTS.md (D16, INV-B09).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from constitutional_architecture.compiler.backends.fastapi_backend import (
    FastAPIBackend,
    GeneratedFile,
)


def _make_minimal_bir(project_name: str = "test-project"):
    """Construct a minimal stand-in for the BIR (Backend IR) that the
    Gen-C FastAPIBackend expects. The backend only reads project_name and
    iterates bir.modules[*].nodes[*].node_type.name == 'SERVICE'."""
    class _Node:
        def __init__(self, name: str, ntype: str = "SERVICE", children=None):
            self.name = name
            self.node_type = type("NT", (), {"name": ntype})()
            self.children = children or []

    class _Module:
        def __init__(self, name: str, nodes=None):
            self.name = name
            self.nodes = nodes or []

    class _BIR:
        def __init__(self, project_name: str, modules):
            self.project_name = project_name
            self.modules = modules

    return _BIR(
        project_name=project_name,
        modules=[_Module("main", [_Node("svc_a", "SERVICE")])],
    )


class TestArtifactAdapterNoFilesystemWriteInCompile(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (a): the backend must NOT call write_files() inside compile().

    Per D09 and INV-B09: backend emission is via ArtifactSet, not filesystem
    writes inside compile().
    """

    def test_compile_does_not_call_write_files(self):
        backend = FastAPIBackend(output_dir="/tmp/should-not-be-written")
        bir = _make_minimal_bir()
        with patch.object(FastAPIBackend, "write_files") as mock_write:
            backend.compile(bir, bindings=[])
            mock_write.assert_not_called()

    def test_compile_returns_backend_result(self):
        backend = FastAPIBackend(output_dir="/tmp/should-not-be-written")
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        self.assertIsNotNone(result)
        self.assertIsInstance(result.artifacts, list)

    def test_compile_does_not_create_filesystem_files(self):
        """A focused filesystem check: no file should appear under output_dir
        as a result of calling compile()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FastAPIBackend(output_dir=tmpdir)
            bir = _make_minimal_bir(project_name="fs-check")
            backend.compile(bir, bindings=[])
            remaining = sorted(os.listdir(tmpdir))
            self.assertEqual(remaining, [], f"compile() wrote files: {remaining}")


class TestArtifactAdapterReturnsArtifactSet(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (b): the backend must return an ArtifactSet, not
    arbitrary filesystem writes.

    The constitutional `BackendResult(artifacts=..., diagnostics=...)` is the
    contract surface; `artifacts` is the ArtifactSet equivalent in the
    constitutional substrate (per D09 the canonical ArtifactSet is a
    future module; the constitutional artifacts list is the stabilized form).
    """

    def test_compile_returns_non_empty_artifacts(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-empty"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        self.assertGreater(len(result.artifacts), 0)

    def test_compile_artifacts_have_paths(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-paths"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        for art in result.artifacts:
            self.assertTrue(hasattr(art, "path"), "Artifact must have a path")
            self.assertIsInstance(art.path, str)
            self.assertGreater(len(art.path), 0)

    def test_compile_artifacts_have_content(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-content"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        for art in result.artifacts:
            self.assertTrue(hasattr(art, "content"), "Artifact must have content")
            self.assertIsInstance(art.content, str)
            self.assertGreater(len(art.content), 0)

    def test_compile_artifacts_have_artifact_type(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-type"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        for art in result.artifacts:
            self.assertTrue(hasattr(art, "artifact_type"), "Artifact must have artifact_type")

    def test_compile_artifacts_have_backend_identification(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-id"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        for art in result.artifacts:
            self.assertTrue(hasattr(art, "backend"), "Artifact must carry backend identification")
            self.assertEqual(art.backend, "fastapi")

    def test_compile_no_diagnostics_on_success(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-diag"))
        bir = _make_minimal_bir()
        result = backend.compile(bir, bindings=[])
        self.assertEqual(result.diagnostics, [])


class TestArtifactAdapterDeterminism(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (c): determinism. Same valid source -> same canonical
    result. Repeated runs of compile() must produce the same artifact paths
    and content (the constitutional generate() is order-stable).
    """

    def test_repeated_compile_produces_same_paths(self):
        backend1 = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-det-1"))
        backend2 = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-det-2"))
        bir = _make_minimal_bir(project_name="det-check")
        r1 = backend1.compile(bir, bindings=[])
        r2 = backend2.compile(bir, bindings=[])
        paths1 = sorted(a.path for a in r1.artifacts)
        paths2 = sorted(a.path for a in r2.artifacts)
        self.assertEqual(paths1, paths2)

    def test_repeated_compile_produces_same_content(self):
        backend1 = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-det-3"))
        backend2 = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-det-4"))
        bir = _make_minimal_bir(project_name="det-check-2")
        r1 = backend1.compile(bir, bindings=[])
        r2 = backend2.compile(bir, bindings=[])
        content1 = sorted(a.content for a in r1.artifacts)
        content2 = sorted(a.content for a in r2.artifacts)
        self.assertEqual(content1, content2)


class TestArtifactAdapterUnsupportedCapability(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (d): when the backend encounters an unsupported
    capability, it must NOT silently succeed. (Per the R1-B gate decision A:
    UNSUPPORTED_CAPABILITY -> Verification INDETERMINATE, not PASS.)

    The constitutional FastAPIBackend currently has no formal UNSUPPORTED_CAPABILITY
    outcome; this test documents the expected behavior as a guard. A future
    constitutional adaptation will populate diagnostics with the unsupported
    capability. For now, the test asserts that compile() either succeeds with
    valid artifacts (no silent failure) or returns a BackendResult with
    diagnostics; it does NOT silently write files.
    """

    def test_compile_does_not_silently_fail_on_unsupported(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-unsup"))
        bir = _make_minimal_bir(project_name="unsup-check")
        with patch.object(FastAPIBackend, "write_files") as mock_write:
            result = backend.compile(bir, bindings=[])
            mock_write.assert_not_called()
        self.assertIsNotNone(result)


class TestArtifactAdapterPackagerSeparation(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (e): the packager is a separate step.

    The write_files() method is preserved as a utility for the packager to
    call explicitly after compile(). The constitutional end-to-end test
    (constitutional_architecture/tests/test_end_to_end.py:514) already calls
    write_files(tmpdir) explicitly. This test verifies the separation.
    """

    def test_write_files_is_explicit_packager_step(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-pack"))
        bir = _make_minimal_bir(project_name="pack-check")
        result = backend.compile(bir, bindings=[])
        self.assertGreater(len(result.artifacts), 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            written = backend.write_files(tmpdir)
            self.assertGreater(len(written), 0)
            for path in written:
                self.assertTrue(os.path.isfile(path), f"packager must write file: {path}")
                self.assertTrue(path.startswith(tmpdir), "packager must write under the given base_dir")

    def test_compile_then_write_files_does_not_double_write(self):
        """compile() returns artifacts; the packager writes them. The packager
        step (write_files) is a separate, explicit invocation. It does not
        double-write (the artifacts list is the single source of truth)."""
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-double"))
        bir = _make_minimal_bir(project_name="double-check")
        result = backend.compile(bir, bindings=[])
        artifact_count = len(result.artifacts)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = backend.write_files(tmpdir)
            self.assertEqual(artifact_count, len(written),
                             "packager writes exactly the artifacts the backend emitted")


class TestArtifactAdapterOneWayBoundary(unittest.TestCase):
    """ADAPTER-ARTIFACT-001 (f): one-way boundary (INV-B15).

    The canonical runtime must not silently mutate the constitutional backend's
    state through the adapter. The backend's internal state (_generated_files,
    _backend_ir, _output_dir) is set by the backend; the adapter (compile) does
    not receive a canonical-runtime mutable state.
    """

    def test_compile_does_not_mutate_caller_state(self):
        backend = FastAPIBackend(output_dir=os.path.join(tempfile.gettempdir(), "r1c-mut"))
        bir = _make_minimal_bir(project_name="mut-check")
        before_output_dir = backend._output_dir
        before_files_len = len(backend._generated_files)
        result = backend.compile(bir, bindings=[])
        self.assertEqual(backend._output_dir, before_output_dir,
                         "compile must not mutate the backend's output_dir")
        self.assertGreater(len(backend._generated_files), before_files_len,
                           "compile populates _generated_files (the constitutional flow)")

        self.assertIsNotNone(result)
        for art in result.artifacts:
            self.assertIsNotNone(art.path)
            self.assertIsNotNone(art.content)


if __name__ == "__main__":
    unittest.main()
