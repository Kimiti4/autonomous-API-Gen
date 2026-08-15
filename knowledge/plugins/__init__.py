"""
Knowledge Graph plugin runtime.

This package defines the plugin architecture for external and replaceable
Knowledge Graph backends.

Supported plugin capabilities include:
- graph storage
- search storage
- embeddings
- visualization

Constitutional constraints:
- The Knowledge Graph core must not depend on a specific backend technology.
- Plugins must satisfy explicit contracts.
- Plugins must expose health checks.
- Plugins must remain replaceable.
"""

__version__ = "0.1.0"
