"""Tests for via54_larkgroups.archive.

Verify markdown formatting, timezone handling, empty case.
"""
import datetime
import sqlite3
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups import sync, archive as archive_mod, config


@pytest.fixture
def tmp_vault(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VAULT_DB", tmp_path / "vault.db")
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(config, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.log")
    return tmp_path


class TestArchiveDay:
    def test_empty_db_produces_valid_md(self, tmp_vault):
        sync.init_db()
        result = archive_mod.archive_day(target_date=datetime.date(2026, 6, 24))
        md_path = Path(result["md_path"])
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "# Feishu Chat Archive" in content
        assert "2026-06-24" in content
        assert result["messages"] == 0
        assert result["chats"] == 0

    def test_messages_grouped_by_chat(self, tmp_vault):
        sync.init_db()
        # Insert test data
        conn = sqlite3.connect(str(config.VAULT_DB))
        c = conn.cursor()
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?)",
                  ("chat1", "group", "Test Group", "2026-06-24T10:00:00+00:00"))
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?)",
                  ("chat2", "p2p", "DM with Bob", "2026-06-24T10:00:00+00:00"))
        c.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("m1", "chat1", "group", "u1", "Alice", "text", "hello",
             "2026-06-24T02:00:00+00:00", "2026-06-24T02:00:01+00:00", 0, None),
        )
        c.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("m2", "chat2", "p2p", "u2", "Bob", "text", "hi back",
             "2026-06-24T02:01:00+00:00", "2026-06-24T02:01:01+00:00", 0, None),
        )
        conn.commit()
        conn.close()

        result = archive_mod.archive_day(target_date=datetime.date(2026, 6, 24))
        content = Path(result["md_path"]).read_text(encoding="utf-8")

        # Both chat headers present
        assert "## Test Group" in content
        assert "## DM with Bob" in content
        # Messages present
        assert "hello" in content
        assert "hi back" in content
        # Timestamps in CST
        assert "10:00:00" in content  # 02:00 UTC = 10:00 CST
        assert result["messages"] == 2
        assert result["chats"] == 2

    def test_messages_filtered_by_date(self, tmp_vault):
        """Messages outside the target date should NOT appear."""
        sync.init_db()
        conn = sqlite3.connect(str(config.VAULT_DB))
        c = conn.cursor()
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?)",
                  ("chat1", "group", "Test", "2026-06-23T10:00:00+00:00"))
        # Yesterday's message
        c.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("m_old", "chat1", "group", "u1", "Alice", "text", "old message",
             "2026-06-23T15:00:00+00:00", "2026-06-23T15:00:01+00:00", 0, None),
        )
        conn.commit()
        conn.close()

        result = archive_mod.archive_day(target_date=datetime.date(2026, 6, 24))
        content = Path(result["md_path"]).read_text(encoding="utf-8")
        assert "old message" not in content
        assert result["messages"] == 0


class TestTimezoneConversion:
    def test_cst_default(self, tmp_vault):
        """Default timezone offset should be +8 (CST)."""
        import inspect
        sig = inspect.signature(archive_mod.archive_day)
        # tz_offset_hours is the 2nd param (after target_date)
        assert sig.parameters["tz_offset_hours"].default == 8

    def test_custom_offset(self, tmp_vault):
        sync.init_db()
        # No data, just verify it runs with custom offset
        result = archive_mod.archive_day(
            target_date=datetime.date(2026, 6, 24),
            tz_offset_hours=-5,  # EST
        )
        assert Path(result["md_path"]).exists()