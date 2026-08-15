from pathlib import Path
from ...domain.ports import CompilerBackend
from ...domain.models.bundle import SystemDeploymentBundle
from ...domain.models.capability_manifest import BundleCapability, CapabilityManifest
from ...domain.models.genome import Genome
from ...domain.models.isr import IntermediateSoftwareRepresentation


class MinimalContainerBackend:
    """Minimal compiler backend: materializes an ISR into a runnable app dir
    with a smoke test. Swap in real backends (FastAPI/Go/Rust/Java) via the
    CompilerBackend protocol."""

    @property
    def name(self) -> str:
        return "minimal"

    def compile(
        self,
        isr: IntermediateSoftwareRepresentation,
        genome: Genome,
        output_dir: str,
    ) -> SystemDeploymentBundle:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "README.md").write_text(
            f"# {isr.system_name}\nISR: {isr.system_id}\n"
            f"Lineage: {', '.join(isr.lineage) or 'none'}\n"
        )
        tests = out / "tests"
        tests.mkdir(exist_ok=True)
        (tests / "test_smoke.py").write_text("def test_smoke():\n    assert True\n")
        (out / "app.py").write_text("def health():\n    return {'status': 'ok'}\n")
        manifest = CapabilityManifest(
            backend_id=self.name,
            capabilities=[
                BundleCapability.CONTAINERIZE,
                BundleCapability.TEST,
                BundleCapability.HEALTH_CHECK,
            ],
        )
        return SystemDeploymentBundle(
            project_id=isr.system_id,
            backend_name=self.name,
            isr_hash=isr.content_hash(),
            path=out,
            artifacts=["README.md", "app.py", "tests/test_smoke.py"],
            capability_manifest=manifest,
        )
