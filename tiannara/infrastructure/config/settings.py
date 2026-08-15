from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """All routing identity and thresholds are injected from the environment.

    Nothing is hardcoded. See ``.env.example``. ``github_token`` is optional:
    when absent the publisher falls back to ``LocalRepositoryPublisher`` so the
    calibration harness is runnable without GitHub credentials.
    """

    model_config = SettingsConfigDict(env_prefix="TIANNARA_", env_file=".env")

    github_token: SecretStr | None = None
    fallback_owner: str = "kimiti4"
    fallback_email: str = "karamos473@gmail.com"

    min_test_pass_rate: float = 0.995
    require_compilation: bool = True
    require_security_scan: bool = False
    max_security_vulnerabilities: int = 0

    max_concurrency: int = 5
    verification_timeout_seconds: int = 300
    quarantine_dir: str = "./tiannara-quarantine"
    ledger_path: str = "./tiannara-evidence/calibration-ledger.jsonl"
    environment: str = "auto"
