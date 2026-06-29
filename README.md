# via54Larkgroups

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Stdlib](https://img.shields.io/badge/dependencies-stdlib--only-brightgreen)](requirements.txt)
[![Status](https://img.shields.io/badge/status-beta-yellow)](CHANGELOG.md)

> **Local-only** Feishu (Lark) chat archive tool. Pulls your daily chat history and exports it as Markdown + raw files. **No data ever leaves your machine.**

[中文文档](docs/setup_zh.md) · [Quick Start](#quick-start) · [Security Model](#security-model) · [Contributing](CONTRIBUTING.md)

---

## What is it?

`via54Larkgroups` is a CLI tool that:

1. Logs into your Feishu account via OAuth 2.0 (browser-based, you approve)
2. Pulls the last 24 hours of chat messages from your chats and groups
3. Stores them in a local SQLite database
4. Exports them as Markdown (`YYYY-MM-DD.md`) with attachments preserved
5. (Optional) Auto-syncs daily at 3 AM local time

It is designed for **personal archival** — like a private Notion vault of your work conversations. Not for spying, monitoring others, or uploading data anywhere.

---

## Why?

- Feishu's official export only covers a single chat at a time and doesn't include attachments
- Third-party SaaS tools cost money and require trusting a third party with all your messages
- This tool keeps everything on your disk and gives you full control

---


## 🔗 集成 (v1.1.0 新增)

via54Larkgroups v1.1.0 跟踪 3 个高星聊天归档项目, 计划扩展到多平台 (Slack/Discord/Telegram):

- [KnugiHK/WhatsApp-Chat-Exporter](https://github.com/KnugiHK/WhatsApp-Chat-Exporter) (1.1K) - Cross-platform WhatsApp chat databases
- [knadh/tg-archive](https://github.com/knadh/tg-archive) (1.1K) - Telegram group chats -> static websites
- [mahtoid/DiscordChatExporterPy](https://github.com/mahtoid/DiscordChatExporterPy) (283) - Discord channel chats to HTML

详见 [integrations/README.md](integrations/README.md) 和 [REFERENCES.md](REFERENCES.md).

---

## Quick Start

### 1. Install (from source, requires Python 3.11+)

```bash
git clone https://github.com/via54/via54Larkgroups.git
cd via54Larkgroups
pip install -e .
```

### 2. Create a Feishu App (one-time, ~10 min)

See [docs/setup_zh.md](docs/setup_zh.md) for step-by-step with screenshots.

Required OAuth scopes (only these 3, never more):
- `im:message:readonly`
- `im:message.group_at_msg:readonly`
- `contact:user.base:readonly`

### 3. Save credentials

```bash
feishu-vault config --app-id "cli_xxx" --app-secret "yyy"
```

### 4. Login (browser OAuth)

```bash
feishu-vault login
```

Opens browser → Feishu login page → approve → token saved locally (expires in 24h).

### 5. Sync today's chats

```bash
feishu-vault sync
```

Metadata only by default (text + sender + timestamp + file names).

To also download attachment files:

```bash
feishu-vault sync --include-attachments
```

⚠️ This will download images / videos / docs to your disk. You get a 5-second countdown to abort.

### 6. Export to Markdown

```bash
feishu-vault archive
```

Output: `~/AppData/Local/hermes/feishu_vault/archive/2026-06-24/2026-06-24.md`

---

## Security Model

| Aspect | Guarantee |
|--------|-----------|
| **Data location** | All data lives in `~/AppData/Local/hermes/feishu_vault/` |
| **Network targets** | Only `open.feishu.cn` and `passport.feishu.cn` |
| **OAuth scope** | Hardcoded allowlist of 3 read-only scopes |
| **Token TTL** | Forced to 24h, expired tokens force re-login |
| **Default state** | OFF — every sync/archive is manual unless you opt in |
| **Auto-sync opt-in** | Requires explicit `--enable-auto-sync` flag |
| **Stop button** | `feishu-vault stop` halts background sync within 5s |
| **Audit log** | Every sync writes `count + bytes + scope` to `audit.log` |
| **Write capability** | NONE — the tool cannot send messages on your behalf |

### Verified

```bash
# Should ONLY show open.feishu.cn and passport.feishu.cn
grep -rn "https://" src/ | grep -v "open.feishu.cn\|passport.feishu.cn"
# (no output = clean)
```

---

## Architecture

```
via54Larkgroups/
├── src/via54_larkgroups/       # Python package
│   ├── __init__.py             # version + exports
│   ├── __main__.py             # CLI entry point (argparse)
│   ├── config.py               # paths, OAuth scope constants, TTL
│   ├── api_client.py           # Feishu Open API client (urllib stdlib)
│   ├── oauth.py                # browser-based OAuth flow (PKCE)
│   ├── sync.py                 # pull messages → SQLite
│   └── archive.py              # SQLite → Markdown + files
├── tests/                      # pytest test suite (no network mocks)
├── docs/                       # detailed documentation
├── examples/                   # sample configs (gitignored)
├── scripts/                    # OS wrappers (feishu-vault.bat, .sh)
├── .github/                    # GitHub Actions + templates
├── pyproject.toml              # modern Python project metadata
├── requirements.txt            # deps (stdlib only)
├── .gitignore                  # excludes tokens, DB, configs
├── LICENSE                     # MIT
└── README.md                   # this file
```

### Data Flow

```
Feishu API ──OAuth──> token.json (24h)
       │
       │ sync_today()
       ▼
   vault.db (SQLite) ──archive_day()──> archive/YYYY-MM-DD/YYYY-MM-DD.md
                                          + attachments/...
```

---

## Command Reference

| Command | Purpose |
|---------|---------|
| `feishu-vault config --app-id X --app-secret Y` | Save Feishu App credentials |
| `feishu-vault login` | Browser OAuth login (24h token) |
| `feishu-vault logout` | Clear saved token |
| `feishu-vault status` | Show token / DB / auto-sync state |
| `feishu-vault sync` | Pull last 24h of chats (metadata only) |
| `feishu-vault sync --include-attachments` | Pull chats + download files |
| `feishu-vault archive` | Export today to Markdown |
| `feishu-vault archive --date 2026-06-23` | Export specific date |
| `feishu-vault search --keyword X` | Search archived markdown files |
| `feishu-vault --enable-auto-sync` | Enable daily background sync (opt-in) |
| `feishu-vault stop` | Stop all background sync within 5s |

---

## Limitations

- **Hardcoded 24h window**: `sync` always pulls last 24 hours. To archive older chats, run sync daily for N days.
- **No rich message types**: text, image, file, audio, video, sticker are captured but only text is searchable in Markdown export.
- **One Feishu account per data dir**: `token.json` stores one user_access_token. Switch account = `logout` + re-login.
- **Chinese-only tested**: timestamps use CST (+8) by default; adjust `tz_offset_hours` in `archive.py` for other zones.

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Built as a personal data-ownership project. OAuth flow modeled on the [Feishu Open Platform docs](https://open.feishu.cn/document/server-docs/authentication-management/access-token/overview). No affiliation with Feishu / ByteDance.

## Status

Beta. Tested on Windows 11 + Python 3.11.15. Linux/macOS should work (uses only stdlib + a free local port for OAuth callback).