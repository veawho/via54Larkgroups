"""Tests for via54_larkgroups.__main__ CLI.

Verify command parsing, subcommand dispatch, top-level flags.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups.__main__ import main


class TestCLIParsing:
    def test_help_works(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_enable_auto_sync_top_level(self, tmp_path, monkeypatch, capsys):
        from via54_larkgroups import config
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "v")
        monkeypatch.setattr(config, "AUTO_SYNC_FLAG", config.DATA_ROOT / "auto_sync.enabled")
        monkeypatch.setattr(config, "AUDIT_LOG", config.DATA_ROOT / "audit.log")
        rc = main(["--enable-auto-sync"])
        assert rc == 0
        assert config.AUTO_SYNC_FLAG.exists()
        captured = capsys.readouterr()
        assert "Auto-sync ENABLED" in captured.out

    def test_status_runs_without_token(self, tmp_path, monkeypatch, capsys):
        from via54_larkgroups import config
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "v")
        monkeypatch.setattr(config, "AUTO_SYNC_FLAG", config.DATA_ROOT / "auto_sync.enabled")
        monkeypatch.setattr(config, "TOKEN_FILE", config.DATA_ROOT / "token.json")
        monkeypatch.setattr(config, "CONFIG_FILE", config.DATA_ROOT / "config.json")
        monkeypatch.setattr(config, "VAULT_DB", config.DATA_ROOT / "vault.db")
        monkeypatch.setattr(config, "AUDIT_LOG", config.DATA_ROOT / "audit.log")
        rc = main(["status"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "=== feishu-vault status ===" in captured.out
        assert "Token: NONE" in captured.out

    def test_sync_without_token_errors(self, tmp_path, monkeypatch, capsys):
        from via54_larkgroups import config
        monkeypatch.setattr(config, "DATA_ROOT", tmp_path / "v")
        monkeypatch.setattr(config, "TOKEN_FILE", config.DATA_ROOT / "token.json")
        monkeypatch.setattr(config, "CONFIG_FILE", config.DATA_ROOT / "config.json")
        monkeypatch.setattr(config, "AUDIT_LOG", config.DATA_ROOT / "audit.log")
        rc = main(["sync"])
        assert rc == 2  # error code
        captured = capsys.readouterr()
        assert "No valid token" in captured.out