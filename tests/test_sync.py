"""Tests for via54_larkgroups.sync.

Verify DB schema, stop signal handling, attachment metadata (no network).
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups import sync, config


@pytest.fixture
def tmp_vault(tmp_path, monkeypatch):
    """Redirect DB + paths to temp directory."""
    monkeypatch.setattr(config, "VAULT_DB", tmp_path / "vault.db")
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(config, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.log")
    monkeypatch.setattr(config, "SYNC_STOP_FILE", tmp_path / "sync.stop")
    monkeypatch.setattr(config, "AUTO_SYNC_FLAG", tmp_path / "auto_sync.enabled")
    return tmp_path


class TestDBSchema:
    def test_init_creates_tables(self, tmp_vault):
        sync.init_db()
        conn = sqlite3.connect(str(config.VAULT_DB))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "messages" in tables
        assert "chats" in tables
        assert "attachments" in tables

    def test_init_idempotent(self, tmp_vault):
        sync.init_db()
        sync.init_db()  # Should not raise
        assert config.VAULT_DB.exists()


class TestStopSignal:
    def test_should_stop_returns_false_when_no_file(self, tmp_vault):
        assert sync._should_stop() is False

    def test_should_stop_returns_true_when_file_exists(self, tmp_vault):
        config.SYNC_STOP_FILE.touch()
        assert sync._should_stop() is True

    def test_auto_sync_exits_on_stop(self, tmp_vault):
        # Don't enable flag → loop should exit immediately
        config.AUTO_SYNC_FLAG.unlink(missing_ok=True)
        sync.auto_sync_loop(token_provider=lambda: None)  # should return quickly


class TestTokenProvider:
    def test_no_token_breaks_loop(self, tmp_vault):
        config.AUTO_SYNC_FLAG.touch()
        # Token provider returns None → loop should exit
        start = time.time()
        sync.auto_sync_loop(token_provider=lambda: None)
        elapsed = time.time() - start
        assert elapsed < 1  # exited immediately, didn't wait 24h


class TestAuditOnActions:
    def test_init_db_writes_no_audit(self, tmp_vault):
        sync.init_db()
        # init_db itself doesn't write audit, only sync does
        # This test just ensures no spurious audit entries
        if config.AUDIT_LOG.exists():
            content = config.AUDIT_LOG.read_text(encoding="utf-8")
            # If anything is written, it shouldn't be from init_db
            # (currently init_db doesn't write)
            assert "init_db" not in content