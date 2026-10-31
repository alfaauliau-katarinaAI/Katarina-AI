"""Static regression guard for oauth_gateway/server.js.

Ensures that:
1. /oauth/status and lastAuth do not store or expose MQL5 user profile data or sensitive tokens.
2. The server binds to 127.0.0.1 (loopback) by default instead of 0.0.0.0.
3. No sensitive credentials or tokens (access_token, refresh_token, client_secret) are exposed in status responses or logs.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_JS_PATH = REPO_ROOT / "oauth_gateway" / "server.js"


class OAuthGatewayStaticGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server_js_content = SERVER_JS_PATH.read_text(encoding="utf-8")

    def test_server_js_exists(self) -> None:
        self.assertTrue(SERVER_JS_PATH.is_file(), "oauth_gateway/server.js must exist")

    def test_no_profile_in_last_auth_state(self) -> None:
        """lastAuth state must only store {ok, at, error} without profile."""
        self.assertNotIn(
            "profile:",
            self.server_js_content,
            "oauth_gateway/server.js must not store or expose 'profile' field in lastAuth or /oauth/status",
        )

    def test_default_loopback_host_binding(self) -> None:
        """Server must default to 127.0.0.1 loopback host, not 0.0.0.0."""
        self.assertNotIn(
            "server.listen(PORT, '0.0.0.0'",
            self.server_js_content,
            "oauth_gateway/server.js must not bind to '0.0.0.0' by default",
        )
        self.assertIn(
            "127.0.0.1",
            self.server_js_content,
            "oauth_gateway/server.js must specify '127.0.0.1' as default host binding",
        )

    def test_no_sensitive_tokens_in_oauth_status(self) -> None:
        """Ensure sensitive tokens and credentials are not returned in status endpoint."""
        # Find the block for pathname === '/oauth/status'
        status_idx = self.server_js_content.find("'/oauth/status'")
        self.assertNotEqual(status_idx, -1, "Endpoint '/oauth/status' must exist in server.js")

        status_block = self.server_js_content[status_idx : status_idx + 300]
        for sensitive in ["access_token", "refresh_token", "client_secret", "credentials", "profile"]:
            self.assertNotIn(
                sensitive,
                status_block,
                f"Endpoint '/oauth/status' must not return sensitive field '{sensitive}'",
            )


if __name__ == "__main__":
    unittest.main()
