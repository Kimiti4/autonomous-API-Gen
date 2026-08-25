"""34.23 Container/Runtime -- boundary, filesystem, network."""
from __future__ import annotations
def is_filesystem_escape(path: str) -> bool:
    return ".." in path or path.startswith("/host")
def is_network_exposure(port: int, allowed: set[int]) -> bool:
    return port not in allowed
