"""Tests for via54_larkgroups.config.

Verify constants are NOT silently weakened, paths are sane, audit log works.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Add src to path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups import config


class TestOAuthScopeAllowlist:
    """Hardcoded scope guardrails. These tests should NEVER need updating."""

    def test_only_readonly_scopes(self):
        for scope in config.ALLOWED_SCOPES:
            assert "readonly" in scope or ":base" in scope, (
                f"Scope {scope!r} does not look like a read-only / base scope"
            )

    def test_no_write_capability(self):
        for forbidden in ["im:message:send", "im:message"]:
            assert forbidden not in config.ALLOWED_SCOPES
            assert forbidden not in config.SCOPE_ALLOWLIST

    def test_no_offline_access(self):
        """offline_access would give longer-lived tokens; must NOT be requested."""
        assert "offline_access" not in config.ALLOWED_SCOPES

    def test_allowlist_is_frozenset_or_set(self):
        assert isinstance(config.SCOPE_ALLOWLIST, (set, frozenset))

    def test_allowlist_matches_allowed_list(self):
        assert config.SCOPE_ALLOWLIST == set(config.ALLOWED_SCOPES)


class TestTokenTTL:
    def test_exactly_24_hours(self):
        assert config.USER_TOKEN_TTL_SECONDS == 24 * 3600

    def test_no_week_long_token(self):
        assert config.USER_TOKEN_TTL_SECONDS <= 24 * 3600


class TestPaths:
    def test_data_root_under_hermes(self):
        """Data must live under HERMES_HOME (standard for this machine)."""
        assert "hermes" in str(config.DATA_ROOT).lower()

    def test_no_tmp_paths(self):
        assert "/tmp/" not in str(config.DATA_ROOT)
        assert "C:\\Windows\\" not in str(config.DATA_ROOT)


class TestEnsureDirs:
    def test_creates_dirs(self, tmp_path, monkeypatch):
        # Redirect DATA_ROOT to tmp
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "feishu_vault_test")
        monkeypatch.setattr(config, "ARCHIVE_DIR", config.DATA_ROOT / "archive")
        monkeypatch.setattr(config, "AUDIT_LOG", config.DATA_ROOT / "audit.log")
        config.ensure_dirs()
        assert config.DATA_ROOT.exists()
        assert config.ARCHIVE_DIR.exists()


class TestAuditLog:
    def test_writes_json_line(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "audit_test")
        monkeypatch.setattr(config, "AUDIT_LOG", config.DATA_ROOT / "audit.log")
        config.write_audit("test_action", count=42, foo="bar")
        content = config.AUDIT_LOG.read_text(encoding="utf-8")
        assert content.endswith("\n")
        entry = json.loads(content.strip())
        assert entry["action"] == "test_action"
        assert entry["count"] == 42
        assert entry["foo"] == "bar"
        assert "ts" in entry
        assert "Z" in entry["ts"] or "+" in entry["ts"]  # ISO 8601 UTC