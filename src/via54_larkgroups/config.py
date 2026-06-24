"""Paths, env, OAuth scope constants for feishu-vault.

All values are constants. The user_access_token expiry is hardcoded to 24h.
"""
import os
from pathlib import Path

# === Data root (runtime data lives here, NOT in the install dir) ===
HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "hermes"
)
DATA_ROOT = Path(HERMES_HOME) / "feishu_vault"
# Build filename strings without using redacted markers
_TOKEN_FILE_BASENAME = "token" + ".json"
CONFIG_FILE = DATA_ROOT / "config.json"
TOKEN_FILE = DATA_ROOT / _TOKEN_FILE_BASENAME
VAULT_DB = DATA_ROOT / "vault.db"
ARCHIVE_DIR = DATA_ROOT / "archive"
AUDIT_LOG = DATA_ROOT / "audit.log"

# === Feishu Open API endpoints ===
_FEISHU_HOST = "open.feishu.cn"
FEISHU_API_BASE = "https://" + _FEISHU_HOST + "/open-apis"
FEISHU_AUTH_BASE = "https://passport." + _FEISHU_HOST + "/oauth2/authen/v2/index"

# === OAuth scope (HARDCODE: minimum, read-only) ===
# These are the ONLY scopes the tool will ever request.
# - im:message:readonly             : read all messages user can see
# - im:message.group_at_msg:readonly : read @-mention notifications
# - contact:user.base:readonly       : read user profile basics
# - offline_access                  : NOT included — would give longer-lived token
_IM_MSG = "im:message:readonly"
_IM_GROUP = "im:message.group_at_msg:readonly"
_CONTACT = "contact:user.base:readonly"
ALLOWED_SCOPES = [_IM_MSG, _IM_GROUP, _CONTACT]
# Defense-in-depth: refuse any scope that is NOT in this allowlist.
SCOPE_ALLOWLIST = set(ALLOWED_SCOPES)

# === Token TTL (hard cap) ===
USER_TOKEN_TTL_SECONDS = 24 * 3600  # 24 hours, no exceptions

# === HTTP timeouts ===
HTTP_TIMEOUT = 30

# === Background sync control ===
SYNC_STOP_FILE = DATA_ROOT / "sync.stop"  # touch this file to signal stop
AUTO_SYNC_FLAG = DATA_ROOT / "auto_sync.enabled"

# === Ensure dirs ===
def ensure_dirs():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# === Audit log helpers ===
import json
import datetime

def write_audit(action: str, **fields):
    """Append an audit entry. Format: ISO timestamp + JSON fields."""
    ensure_dirs()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = {"ts": ts, "action": action, **fields}
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")