"""Sync engine: pull messages from Feishu into local SQLite DB.

Local DB schema:
  messages(message_id PK, chat_id, chat_type, sender_id, sender_name,
           msg_type, text, created_at, fetched_at, has_attachment,
           attachment_json)
  chats(chat_id PK, chat_type, name, last_synced_at)
  attachments(message_id, file_key, file_name, file_size, sha256, local_path,
              downloaded)
"""
import datetime
import hashlib
import json
import sqlite3
import time

from . import config
from .api_client import FeishuClient, FeishuAPIError


SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id TEXT PRIMARY KEY,
    chat_type TEXT,
    name TEXT,
    last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    chat_type TEXT,
    sender_id TEXT,
    sender_name TEXT,
    msg_type TEXT,
    text TEXT,
    created_at TEXT,
    fetched_at TEXT NOT NULL,
    has_attachment INTEGER DEFAULT 0,
    attachment_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

CREATE TABLE IF NOT EXISTS attachments (
    message_id TEXT,
    file_key TEXT,
    file_name TEXT,
    file_size INTEGER,
    sha256 TEXT,
    local_path TEXT,
    downloaded INTEGER DEFAULT 0,
    PRIMARY KEY (message_id, file_key)
);
"""


def init_db():
    config.ensure_dirs()
    conn = sqlite3.connect(str(config.VAULT_DB))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def _should_stop() -> bool:
    return config.SYNC_STOP_FILE.exists()


def sync_today(token: dict, include_attachments: bool = False,
               progress=None) -> dict:
    """Sync messages created in the last 24h.

    Returns stats dict: {messages_fetched, chats_scanned, errors, bytes_text}
    """
    init_db()
    stats = {"messages_fetched": 0, "chats_scanned": 0, "errors": 0, "bytes_text": 0}
    client = FeishuClient(token["access_token"])

    # Compute time window: last 24h, end inclusive
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now - datetime.timedelta(hours=24)
    start_ts = str(int(start.timestamp()))
    end_ts = str(int(now.timestamp()))

    # List all chats user is in
    try:
        chats_data = client.list_chats(page_size=50)
    except FeishuAPIError as e:
        config.write_audit("sync_failed_list_chats", error=str(e))
        stats["errors"] += 1
        return stats

    chats = chats_data.get("items", [])
    if progress:
        progress("Found " + str(len(chats)) + " chats")

    conn = sqlite3.connect(str(config.VAULT_DB))
    cur = conn.cursor()

    for chat in chats:
        if _should_stop():
            break
        chat_id = chat.get("chat_id")
        chat_name = chat.get("name", "<unknown>")
        chat_type = chat.get("chat_type", "unknown")
        stats["chats_scanned"] += 1

        # Upsert chat row
        cur.execute(
            "INSERT OR REPLACE INTO chats(chat_id, chat_type, name, last_synced_at) "
            "VALUES (?, ?, ?, ?)",
            (chat_id, chat_type, chat_name, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )

        # List messages in window
        page_token = None
        while True:
            if _should_stop():
                break
            try:
                query = {"chat_id": chat_id, "page_size": 50,
                         "start_time": start_ts, "end_time": end_ts}
                if page_token:
                    query["page_token"] = page_token
                msg_data = client._request("GET", "/im/v1/messages", query=query)
            except FeishuAPIError as e:
                config.write_audit("sync_failed_chat", chat_id=chat_id, error=str(e))
                stats["errors"] += 1
                break

            for msg in msg_data.get("items", []) or []:
                # msg has fields: message_id, chat_id, chat_type, sender_id, msg_type,
                # body.content (JSON-encoded text), create_time, etc.
                msg_id = msg.get("message_id")
                sender_id = msg.get("sender_id", {}).get("id") if isinstance(msg.get("sender_id"), dict) else msg.get("sender_id")
                sender_name = msg.get("sender_name") or ""
                msg_type = msg.get("msg_type", "")
                body = msg.get("body", {})
                content_raw = body.get("content", "{}")
                try:
                    content_obj = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
                except json.JSONDecodeError:
                    content_obj = {"text": content_raw}
                text = content_obj.get("text", "") or ""
                create_time = msg.get("create_time", "")
                # create_time is ms timestamp
                if create_time and create_time.isdigit():
                    create_iso = datetime.datetime.fromtimestamp(
                        int(create_time) / 1000, tz=datetime.timezone.utc
                    ).isoformat()
                else:
                    create_iso = create_time

                has_attachment = 1 if msg_type in ("file", "image", "audio", "media", "sticker") else 0
                attachment_json = json.dumps(content_obj, ensure_ascii=False) if has_attachment else None

                cur.execute(
                    "INSERT OR REPLACE INTO messages"
                    "(message_id, chat_id, chat_type, sender_id, sender_name, msg_type, "
                    " text, created_at, fetched_at, has_attachment, attachment_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (msg_id, chat_id, chat_type, sender_id, sender_name, msg_type,
                     text, create_iso, datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     has_attachment, attachment_json),
                )
                stats["messages_fetched"] += 1
                stats["bytes_text"] += len(text.encode("utf-8"))

                # Attachment handling
                if has_attachment and include_attachments:
                    _download_attachment(client, cur, msg_id, content_obj, msg_type)

            if not msg_data.get("has_more"):
                break
            page_token = msg_data.get("page_token")
            if not page_token:
                break

    conn.commit()
    conn.close()

    config.write_audit("sync_complete",
                       messages=stats["messages_fetched"],
                       chats=stats["chats_scanned"],
                       bytes_text=stats["bytes_text"],
                       errors=stats["errors"],
                       include_attachments=include_attachments)
    return stats


def _download_attachment(client, cur, message_id, content_obj, msg_type):
    """Download attachment body to local file. Records sha256 + size."""
    file_key = content_obj.get("file_key") or content_obj.get("image_key") or ""
    file_name = content_obj.get("file_name") or ("file_" + file_key[:8])
    if not file_key:
        return

    # Get download URL
    try:
        type_map = {"image": "image", "file": "file", "audio": "audio",
                    "video": "video", "media": "file"}
        type_ = type_map.get(msg_type, "file")
        url_data = client.get_message_resource(message_id, file_key, type_=type_)
    except FeishuAPIError as e:
        config.write_audit("attachment_url_failed", message_id=message_id, error=str(e))
        return

    download_url = url_data.get("url") or url_data.get("temp_download_url")
    if not download_url:
        return

    # Download
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    target_dir = config.DATA_ROOT / "archive" / "attachments" / message_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name

    try:
        import urllib.request
        req = urllib.request.Request(download_url, headers={
            "Authorization": "Bearer " + client.token,
        })
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            body = resp.read()
        target_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        size = len(body)
        cur.execute(
            "INSERT OR REPLACE INTO attachments"
            "(message_id, file_key, file_name, file_size, sha256, local_path, downloaded) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (message_id, file_key, safe_name, size, sha, str(target_path)),
        )
    except Exception as e:
        config.write_audit("attachment_download_failed", message_id=message_id, error=str(e))


def auto_sync_loop(token_provider):
    """Background loop: sync every 24h if AUTO_SYNC_FLAG exists.

    token_provider: callable returning fresh token dict or None (forces re-login)
    """
    config.SYNC_STOP_FILE.unlink(missing_ok=True)
    while config.AUTO_SYNC_FLAG.exists():
        if _should_stop():
            break
        token = token_provider()
        if not token:
            config.write_audit("auto_sync_token_missing")
            break
        try:
            stats = sync_today(token)
            config.write_audit("auto_sync_iteration", **stats)
        except Exception as e:
            config.write_audit("auto_sync_error", error=str(e))
        # Sleep 24h, but check stop flag every 60s
        for _ in range(24 * 60):
            if _should_stop() or not config.AUTO_SYNC_FLAG.exists():
                break
            time.sleep(60)
    config.write_audit("auto_sync_exited")