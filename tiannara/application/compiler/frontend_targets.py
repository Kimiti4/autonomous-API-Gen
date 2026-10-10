"""Frontend compiler capability contracts.

Frontend targets share only the technology-neutral compilation boundary. Their
framework-specific behavior belongs in each compiler and its verified knowledge,
not in a universal frontend rule table.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class FrontendTarget:
    target_id: str
    language: str
    runtime_model: str
    capabilities: Tuple[str, ...]
    build_command: Tuple[str, ...]
    test_command: Tuple[str, ...]
    production_ready: bool = False

FRONTEND_TARGETS = (
    FrontendTarget("react_ts","typescript","browser",("components","client_interactivity","static_build"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("vue_ts","typescript","browser",("components","reactivity","static_build"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("angular_ts","typescript","browser",("components","dependency_injection","routing","forms","ssr","hydration"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("next_ts","typescript","hybrid_web",("react","ssr","ssg","routing","server_components"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("nuxt_ts","typescript","hybrid_web",("vue","ssr","ssg","routing"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("svelte_ts","typescript","browser",("components","compile_time_ui","static_build"),("npm","run","build"),("npm","test"),False),
    FrontendTarget("phoenix_liveview","elixir","server_reactive",("server_rendered_ui","realtime","stateful_sessions"),("mix","compile"),("mix","test"),False),
    FrontendTarget("hologram","elixir","server_client_elixir",("elixir_client","reactivity","server_integration"),("mix","compile"),("mix","test"),False),
    FrontendTarget("scenic","elixir","native_gui",("native_gui","graphics","embedded_ui"),("mix","compile"),("mix","test"),False),
)
