"""
Manifest signing and verification.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from .models import PluginManifestISR


def canonical_json(payload: Dict[str, Any]) -> str:
    """Produce canonical JSON for deterministic hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_signature(payload: Dict[str, Any]) -> str:
    """
    Compute a deterministic signature for a manifest payload.

    Production deployments should replace this with real public-key signing,
    for example Ed25519 or RSA-PSS.
    """
    canonical = canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def manifest_signing_payload(manifest: PluginManifestISR) -> Dict[str, Any]:
    """Return the canonical signing payload for a manifest."""
    return manifest.model_dump(
        mode="json",
        exclude={
            "signature",
            "created_at",
            "id",
        },
    )


def sign_manifest(manifest: PluginManifestISR) -> PluginManifestISR:
    """Sign a manifest in place."""
    payload = manifest_signing_payload(manifest)
    manifest.signature = compute_signature(payload)
    return manifest


def verify_manifest_signature(manifest: PluginManifestISR) -> bool:
    """Verify that a manifest signature is valid."""
    expected = compute_signature(manifest_signing_payload(manifest))
    return manifest.signature == expected
