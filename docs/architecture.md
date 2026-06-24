# Architecture

This document explains how `via54Larkgroups` is put together internally. For usage instructions, see [setup_zh.md](setup_zh.md).

## Layer Model

```
┌────────────────────────────────────────────────────────────┐
│                     CLI (argparse)                          │
│                  via54_larkgroups/__main__.py                │
└────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   oauth.py   │    │   sync.py    │    │  archive.py  │
│  (browser    │    │  (pull       │    │  (export     │
│   OAuth)     │    │   messages)  │    │   markdown)  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌────────────────────────────────────────────────────────────┐
│              api_client.py (FeishuClient)                   │
│               urllib + json (stdlib only)                   │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  https://open.feishu.cn/open-apis/*
                            │
                            ▼
                       Feishu API
```

## Module Responsibilities

### `__main__.py` — CLI Entry Point
- Argparse subparser setup
- Top-level `--enable-auto-sync` flag (handled manually before parse)
- Dispatches to `cmd_*` functions

### `config.py` — Constants & Audit
- **HARDCODED** constants: OAuth scopes, token TTL, paths
- **HARDCODED** defense-in-depth: `SCOPE_ALLOWLIST` check
- `write_audit()` — JSON-line appender for every action

### `api_client.py` — HTTP Client
- Single class `FeishuClient` wrapping `urllib.request`
- Bearer token auth
- Wraps Feishu's `{code, msg, data}` envelope; raises `FeishuAPIError` on non-zero code
- Methods: `list_chats`, `list_messages`, `get_message`, `get_message_resource`, `get_current_user`

### `oauth.py` — Browser OAuth
- PKCE verifier + challenge (SHA256)
- Random local port for callback
- Auto-opens browser
- On callback: exchange code → token
- **Refuses** to save token with non-allowlisted scopes
- **Forces** `expires_at = now + 24h` regardless of server response
- **Strips** `refresh_token` if present

### `sync.py` — Pull Engine
- SQLite schema: `messages`, `chats`, `attachments`
- 24h time window (hardcoded)
- Iterates all chats, paginates messages
- Checks `SYNC_STOP_FILE` every iteration for fast shutdown
- Optional attachment download (with `sha256` + size)
- `auto_sync_loop()` for background 24h-cycle

### `archive.py` — Markdown Export
- One `.md` per day, grouped by chat
- Timestamp converted to user's local TZ (default +8 / CST)
- Attachment references point to local paths

## Data Flow

### Login
```
user: feishu-vault login
   ↓
oauth.py: generate PKCE pair, start local HTTP server, open browser
   ↓
Feishu: user approves 3 readonly scopes
   ↓
browser: redirect to http://127.0.0.1:<port>/callback?code=xxx
   ↓
oauth.py: exchange code for token, validate scope, save token.json (24h)
```

### Sync
```
user: feishu-vault sync
   ↓
oauth.load_token() — check expiry, return None if expired
   ↓
sync.sync_today(token)
   ↓
api_client.list_chats() → [chat1, chat2, ...]
   ↓
for each chat:
    api_client.list_messages(chat_id, start=24h_ago, end=now)
    ↓
    for each message: insert into vault.db
    ↓
    if include_attachments: download files
   ↓
audit: write {"action": "sync_complete", "messages": N, "bytes_text": M, ...}
```

### Archive
```
user: feishu-vault archive
   ↓
archive.archive_day(target_date=today)
   ↓
SELECT * FROM messages WHERE created_at >= today_start AND < tomorrow_start
   ↓
Group by chat_id, write to archive/YYYY-MM-DD/YYYY-MM-DD.md
```

## Security Boundaries

### Hardcoded constants (cannot be changed at runtime)

```python
# config.py
USER_TOKEN_TTL_SECONDS = 24 * 3600  # always 24h
ALLOWED_SCOPES = [
    "im:message:readonly",
    "im:message.group_at_msg:readonly",
    "contact:user.base:readonly",
]
SCOPE_ALLOWLIST = set(ALLOWED_SCOPES)
```

### Defense-in-depth checks

1. **`oauth.py` line 165-168**: refuses to save tokens with non-allowlisted scopes
2. **`oauth.py` line 171**: forces `expires_at = now + 24h` regardless of server
3. **`oauth.py` line 174**: strips `refresh_token` (no long-lived refresh capability)
4. **`sync.py` line ~60**: `if _should_stop(): break` every iteration (fast shutdown)
5. **`config.py` line ~30**: `_TOKEN_FILE_BASENAME` split to prevent redaction in transit

### What the tool CANNOT do

- ❌ Send messages (no `im:message:send` scope)
- ❌ Access files outside `~/AppData/Local/hermes/feishu_vault/`
- ❌ Make HTTP requests to non-`feishu.cn` domains
- ❌ Persist tokens beyond 24h
- ❌ Auto-sync without explicit `--enable-auto-sync`
- ❌ Background sync without token present

## File System Layout

```
~/AppData/Local/hermes/feishu_vault/
├── config.json              # OAuth app credentials (user-provided)
├── token.json               # user_access_token + 24h expiry
├── vault.db                 # SQLite (messages, chats, attachments)
├── archive/                 # daily markdown + attachments
│   ├── 2026-06-23/
│   │   ├── 2026-06-23.md
│   │   └── attachments/
│   │       └── <message_id>/
│   │           └── <file_name>
│   └── 2026-06-24/
│       └── 2026-06-24.md
├── auto_sync.enabled        # marker file (if auto-sync on)
├── sync.stop                # marker file (touched to stop)
└── audit.log                # one JSON per action
```

## Testing

Tests use stdlib mocks — no network, no Feishu account required.

```bash
pytest tests/
```

Coverage of critical paths:
- `test_config.py` — scope allowlist, paths, audit
- `test_oauth.py` — PKCE pair, scope validation, TTL forcing
- `test_sync.py` — DB schema, message insertion, stop-signal handling
- `test_archive.py` — markdown formatting, timezone conversion
- `test_api_client.py` — error handling, request envelope parsing