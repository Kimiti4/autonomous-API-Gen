"""Reference Docker implementations of each pipeline stage."""
from __future__ import annotations
import hashlib
import subprocess
import time
import urllib.request


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class DockerBuilder:
    def build(self, repo_dir: str, tag: str) -> tuple[bool, str]:
        rc, out = _run(["docker", "build", "-t", tag, repo_dir])
        return rc == 0, _h(out)


class DockerTestRunner:
    def run_tests(self, image: str, cmd: list[str]) -> tuple[bool, str]:
        rc, out = _run(["docker", "run", "--rm", image, *cmd])
        return rc == 0, _h(out)


class DockerDeployer:
    def deploy(self, image: str, port: int) -> tuple[bool, str]:
        rc, out = _run(["docker", "run", "-d", "-p", f"{port}:8000", image])
        cid = out.strip().splitlines()[-1] if rc == 0 else ""
        return rc == 0, cid


class HttpRuntimeProber:
    def probe(self, port: int, retries: int = 30, delay: float = 1.0) -> bool:
        for _ in range(retries):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=2
                ) as r:
                    if r.status == 200:
                        return True
            except Exception:
                time.sleep(delay)
        return False


class DockerDestroyer:
    def destroy(self, container_id: str) -> bool:
        rc, _ = _run(["docker", "rm", "-f", container_id])
        return rc == 0
