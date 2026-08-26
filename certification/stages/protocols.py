"""Stage protocols — technology-independent seams for each pipeline stage."""
from __future__ import annotations
from typing import Protocol, Tuple


class Builder(Protocol):
    def build(self, repo_dir: str, tag: str) -> Tuple[bool, str]: ...


class StageTestRunner(Protocol):
    def run_tests(self, image: str, cmd: list[str]) -> Tuple[bool, str]: ...


class Deployer(Protocol):
    def deploy(self, image: str, port: int) -> Tuple[bool, str]: ...


class RuntimeProber(Protocol):
    def probe(self, port: int) -> bool: ...


class Destroyer(Protocol):
    def destroy(self, container_id: str) -> bool: ...


class IndependentVerifier(Protocol):
    def verify(self, repo_dir: str, plan_hash: str, plan_path: str) -> bool: ...
