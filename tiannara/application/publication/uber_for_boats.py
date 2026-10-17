"""Uber for Boats publication example -- explicitly evidence-gated and simulation-aware."""
from tiannara.application.publication.repository_publisher_contract import (
    SystemDeploymentBundle,
    publish_bundle,
)
from tiannara.application.publication.repository_assembler import assemble
from tiannara.application.publication.secret_boundary import is_credential_in_isr
from tiannara.application.publication.providers.github import GitHubProvider
from tiannara.application.publication.deployment_handoff import handoff_to_deployment
from tiannara.application.evolution.ledger import EvolutionLedger


def run_uber_for_boats(
    github_token: str = "",
    ledger: EvolutionLedger | None = None,
    certification_refs: tuple[str, ...] = (),
):
    """Run the example only when real certification refs have already been earned.

    The bundled GitHubProvider is a mock, so any resulting publication remains
    explicitly simulation-only and cannot be reported as deployed or verified.
    """
    idea = "I want an Uber for boats."
    if ledger is None:
        ledger = EvolutionLedger()

    if not certification_refs:
        return {
            "idea": idea,
            "status": "BLOCKED_NO_CERTIFICATION_EVIDENCE",
            "verified": False,
            "published": False,
            "blockers": [
                "No trusted certification evidence references were supplied.",
                "Publication was not attempted; a demo-created CERTIFIED event is not evidence.",
            ],
        }

    # These identifiers are example inputs, not independently earned evidence.
    isr_hash = "isr-uber-boats-001"
    artifact_hash = "artifact-uber-boats-001"
    bundle = SystemDeploymentBundle(
        isr_hash, artifact_hash, certification_refs, "deploy-uber-boats"
    )

    if is_credential_in_isr({"isr": isr_hash}, github_token):
        raise ValueError("credential in ISR blocked")

    files = assemble(bundle)
    if "README.md" not in files or ".github/workflows/ci.yml" not in files:
        raise ValueError("repository assembly did not produce required template files")

    # The provider is explicitly a mock: this cannot establish real publication,
    # CI, deployment, health, or telemetry evidence.
    provider = GitHubProvider(token=github_token)
    result = publish_bundle(
        bundle, provider, ledger, lambda ref: ledger.event_by_ref(ref)
    )
    provider.create_release(result.repo_url, "v1.0.0")
    provider.create_milestone(result.repo_url, "MVP")
    provider.create_issue(result.repo_url, "Implement boat matching")
    provider.configure_branch_protection(result.repo_url)
    provider.configure_security(result.repo_url)

    deployment = handoff_to_deployment(result.repo_url)
    return {
        "idea": idea,
        "bundle": bundle,
        "files": list(files.keys()),
        "repo_url": result.repo_url,
        "ledger_ref": result.ledger_ref,
        "publication_mode": "simulation",
        "status": "SIMULATION_ONLY_DEPLOYMENT_UNVERIFIED",
        "deployment": deployment,
        "verified": False,
        "blockers": [
            "GitHub provider is simulated and does not create a real repository.",
            *deployment["blockers"],
        ],
    }
