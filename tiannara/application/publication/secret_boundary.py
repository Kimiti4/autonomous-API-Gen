"""Secret Boundary -- credential never in ISR/artifact/commit."""
def is_credential_in_isr(isr, credential: str) -> bool:
    if not credential:
        return False
    return credential in str(isr)
def is_credential_in_artifact(artifact: dict, credential: str) -> bool:
    if not credential:
        return False
    return credential in str(artifact)
def is_credential_in_commit(commit_msg: str, credential: str) -> bool:
    if not credential:
        return False
    return credential in commit_msg
