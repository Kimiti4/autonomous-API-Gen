"""Assembler -- SystemDeploymentBundle -> repo files."""
def assemble(bundle) -> dict:
    return {
        "README.md": f"# Tiannara Generated\nArtifact {bundle.artifact_hash}\nISR {bundle.isr_hash}",
        "LICENSE": "MIT",
        "CONTRIBUTING.md": "Contributing guide",
        "CHANGELOG.md": "Changelog",
        "SECURITY.md": "Security policy",
        "CODEOWNERS": "* @tiannara",
        ".github/workflows/ci.yml": "name: CI\non: push",
        ".github/ISSUE_TEMPLATE/bug.md": "bug template",
        ".github/PULL_REQUEST_TEMPLATE.md": "PR template",
    }
