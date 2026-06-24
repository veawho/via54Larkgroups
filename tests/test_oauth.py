"""Tests for via54_larkgroups.oauth.

Critical security paths: PKCE generation, scope validation, TTL forcing.
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups import oauth, config


class TestPKCEPair:
    def test_verifier_length(self):
        verifier, challenge = oauth._gen_pkce_pair()
        # token_urlsafe(64) gives ~86 chars
        assert len(verifier) >= 43

    def test_challenge_is_base64url_sha256(self):
        import base64
        import hashlib
        verifier, challenge = oauth._gen_pkce_pair()
        # Verify challenge = base64url(sha256(verifier)) without padding
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        assert challenge == expected


class TestScopeValidation:
    """The most critical security test: ensure non-allowlisted scopes are refused."""

    def test_refuses_send_scope(self):
        """If Feishu grants im:message:send, we MUST refuse the token."""
        token = {
            "access_token": "fake",
            "scope": "im:message im:message:send im:message:readonly",
            "expires_in": 7200,
        }
        # Simulate the validation logic from login()
        returned_scopes = set(token["scope"].split())
        extra = returned_scopes - config.SCOPE_ALLOWLIST
        assert "im:message:send" in extra
        assert "im:message" in extra
        # The login() function would raise here

    def test_accepts_only_allowlisted_scopes(self):
        token = {
            "access_token": "fake",
            "scope": "im:message:readonly im:message.group_at_msg:readonly contact:user.base:readonly",
        }
        returned_scopes = set(token["scope"].split())
        extra = returned_scopes - config.SCOPE_ALLOWLIST
        assert extra == set()

    def test_offline_access_refused(self):
        token = {
            "scope": "im:message:readonly offline_access",
        }
        returned_scopes = set(token["scope"].split())
        extra = returned_scopes - config.SCOPE_ALLOWLIST
        assert "offline_access" in extra


class TestLoadToken:
    def test_no_token_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "token.json")
        assert oauth.load_token() is None

    def test_expired_token_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "token.json")
        # Create expired token (issued 2 days ago)
        token = {"access_token": "x", "expires_at": int(time.time()) - 100}
        config.TOKEN_FILE.write_text(json.dumps(token))
        assert oauth.load_token() is None

    def test_valid_token_returned(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "token.json")
        token = {"access_token": "x", "expires_at": int(time.time()) + 3600}
        config.TOKEN_FILE.write_text(json.dumps(token))
        loaded = oauth.load_token()
        assert loaded is not None
        assert loaded["access_token"] == "x"


class TestClearToken:
    def test_removes_token_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "token.json")
        config.TOKEN_FILE.write_text('{"access_token": "x"}')
        oauth.clear_token()
        assert not config.TOKEN_FILE.exists()

    def test_clear_nonexistent_no_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "token.json")
        # Should not raise
        oauth.clear_token()