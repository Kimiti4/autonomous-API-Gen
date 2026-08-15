import shutil
from pathlib import Path
from ...domain.ports import RepositoryPublisher


class LocalRepositoryPublisher:
    """Default publisher: mirrors the bundle into a local directory and returns
    a file:// URL. Use GitHubRepositoryPublisher for remote publication."""

    def __init__(self, dest_root: Path) -> None:
        self._dest = Path(dest_root)
        self._dest.mkdir(parents=True, exist_ok=True)

    async def publish(self, bundle, evidence, owner, author_name, author_email) -> str:
        dest = self._dest / evidence.project_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(bundle.path, dest)
        print(f"[PUBLISHED] {evidence.project_id} -> {dest}")
        return f"file://{dest}"
