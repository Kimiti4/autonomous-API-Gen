"""Frontend boundary tests (static): presentation only, no governance.

Asserts the Next.js frontend cannot issue commands, hold tokens, compute
policy, or fabricate epistemic states — structurally, not by convention.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "observatory" / "frontend"


def _sources(suffixes=(".ts", ".tsx", ".mjs", ".css")) -> dict:
    files = {}
    for path in FRONTEND.rglob("*"):
        if path.is_file() and path.suffix in suffixes \
                and "node_modules" not in path.parts \
                and ".next" not in path.parts:
            files[path.relative_to(FRONTEND).as_posix()] = path.read_text(
                encoding="utf-8")
    return files


class PresentationBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = _sources()

    def test_no_command_issuance(self):
        # Client components may POST only to same-origin Next.js routes
        # (/api/auth/*, /api/observatory/command); direct backend paths
        # and raw POSTs elsewhere remain forbidden.
        import re as _re
        for rel, src in self.sources.items():
            if rel.endswith(".css"):
                continue
            # The server-side proxy route is the single legitimate holder
            # of the backend command path; client code must never name it.
            if not rel.startswith("app/api/"):
                self.assertNotIn("/observatory/commands", src, rel)
            for match in _re.finditer(
                    r"fetch\(\s*[\"']([^\"']+)[\"']\s*,?\s*(\{[^}]*\})?",
                    src):
                url = match.group(1)
                options = match.group(2) or ""
                if "POST" in options:
                    self.assertTrue(
                        url.startswith("/api/"),
                        (rel, f"non-proxy POST to {url}"))

    def test_no_privileged_tokens(self):
        # Server-only secrets may appear in route handlers / server libs
        # only — never in browser-bundled client code.
        server_paths = {"app/api/", "lib/auth.ts"}
        for rel, src in self.sources.items():
            if any(rel.startswith(prefix) or rel == prefix.rstrip("/")
                   for prefix in server_paths):
                continue
            for marker in ("OBSERVATORY_API_TOKEN", "OBSERVATORY_BACKEND_TOKEN",
                           "OBSERVATORY_SESSION_SECRET",
                           "OBSERVATORY_OPERATOR_PASSPHRASE"):
                self.assertNotIn(marker, src, (rel, marker))
        # Server-only TOKEN vars are legitimate in .env.example; only
        # NEXT_PUBLIC_-prefixed token exposure is forbidden.
        env_example = (FRONTEND / ".env.example").read_text(encoding="utf-8")
        for match in re.finditer(r"NEXT_PUBLIC_\w+", env_example):
            self.assertEqual(match.group(0),
                             "NEXT_PUBLIC_OBSERVATORY_API_URL")
        for rel, src in self.sources.items():
            if rel.endswith((".ts", ".tsx")):
                for match in re.finditer(r"NEXT_PUBLIC_\w+", src):
                    self.assertEqual(match.group(0),
                                     "NEXT_PUBLIC_OBSERVATORY_API_URL", rel)

    def test_no_policy_logic(self):
        banned = ["isAdmin", "clearance ===", "role ===",
                  "epistemic_status ===", "status ==="]
        for rel, src in self.sources.items():
            if not rel.endswith(".tsx"):
                continue
            for token in banned:
                self.assertNotIn(token, src, (rel, token))

    def test_epistemic_states_covered(self):
        css = self.sources["app/globals.css"]
        component = self.sources["components/EpistemicBadge.tsx"]
        for state in ("unknown", "inferred", "observed", "contradiction"):
            self.assertIn(f"epistemic-{state}", css, state)
        self.assertIn("unknown", component)

    def test_package_pinned_private(self):
        package = json.loads(
            (FRONTEND / "package.json").read_text(encoding="utf-8"))
        self.assertTrue(package["private"])
        for name, version in {**package["dependencies"],
                              **package["devDependencies"]}.items():
            self.assertNotRegex(version, r"[\^~]",
                                f"{name} must be pinned, got {version}")

    def test_workspace_surface_boundaries(self):
        sources = self.sources
        # Workspace proxy requires session; never exposes backend token.
        proxy = sources["app/api/workspaces/[[...path]]/route.ts"]
        self.assertIn("getSession()", proxy)
        self.assertIn("OBSERVATORY_BACKEND_TOKEN", proxy)
        self.assertNotIn("NEXT_PUBLIC_OBSERVATORY_BACKEND_TOKEN", proxy)
        # Workspace lib talks only to the same-origin proxy.
        lib = sources["lib/workspaces.ts"]
        self.assertIn("/api/workspaces", lib)
        self.assertNotIn("127.0.0.1:8000", lib)
        # Save panel warns against secrets in workspace content.
        panel = sources["components/ServerWorkspacePanel.tsx"]
        self.assertIn("Do not store", panel)
        self.assertIn("secrets", panel.lower())

    def test_workspace_audit_wired(self):
        # GAP-004 (D36 T3): the workspaces view must render the audit trail
        # through the existing audit() client. Static surface proof.
        page = self.sources["app/workspaces/page.tsx"]
        self.assertIn("workspacesApi.audit(", page)
        self.assertIn("Hide audit", page)
        self.assertIn("No audit records", page)

    def test_api_client_read_only(self):
        api = self.sources["lib/api.ts"]
        self.assertNotIn("POST", api)
        self.assertNotIn("PUT", api)
        self.assertNotIn("DELETE", api)
        self.assertIn("no-store", api)

    def test_command_proxy_surface(self):
        sources = self.sources
        # Production deployment is not exposable through the console.
        self.assertNotIn("request_production_deploy",
                         sources["lib/commands.ts"])
        # Session cookie is HTTP-only; token never touches the browser.
        login = sources["app/api/auth/login/route.ts"]
        self.assertIn("httpOnly: true", login)
        self.assertIn("timingSafeEqual", login)
        # Command route gates on proxy flag, session, allowlist, rate limit.
        command = sources["app/api/observatory/command/route.ts"]
        for marker in ("OBSERVATORY_COMMAND_PROXY_ENABLED", "getSession()",
                       "allowedActionsForClearance", "rateLimit",
                       "OBSERVATORY_BACKEND_TOKEN"):
            self.assertIn(marker, command, marker)
        self.assertNotIn("NEXT_PUBLIC_OBSERVATORY_BACKEND_TOKEN", command)
        # Failed logins and disabled proxy fail closed with reasons.
        self.assertIn("operator_login_disabled", login)
        # Auth helpers reject unsigned/expired/malformed sessions.
        auth = sources["lib/auth.ts"]
        for marker in ("timingSafeEqual", "Date.now() > parsed.exp",
                       "OBSERVATORY_SESSION_SECRET is not configured"):
            self.assertIn(marker, auth, marker)


if __name__ == "__main__":
    unittest.main()
