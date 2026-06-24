---
layout: default
title: via54Larkgroups
---

# via54Larkgroups

> **Local-only** Feishu (Lark) chat archive tool. Pulls your daily chat history and exports it as Markdown + raw files. **No data ever leaves your machine.**

[中文文档](https://github.com/veawho/via54Larkgroups/blob/main/docs/setup_zh.md) ·
[Quick Start](https://github.com/veawho/via54Larkgroups#quick-start) ·
[Security Model](https://github.com/veawho/via54Larkgroups#security-model) ·
[Contributing](https://github.com/veawho/via54Larkgroups/blob/main/CONTRIBUTING.md)

---

## What is it?

A Python CLI tool that:

1. Logs into your Feishu account via OAuth 2.0 (browser-based, you approve)
2. Pulls the last 24 hours of chat messages
3. Stores them in a local SQLite database
4. Exports them as Markdown (`YYYY-MM-DD.md`) with attachments preserved
5. (Optional) Auto-syncs daily

## Why?

- Feishu's official export only covers a single chat at a time
- Third-party SaaS tools cost money and require trusting them with your messages
- This tool keeps everything on your disk

## Quick Start

### Install

```bash
git clone https://github.com/veawho/via54Larkgroups.git
cd via54Larkgroups
pip install -e .
```

### Create a Feishu App (~10 min, one-time)

See [setup_zh.md](https://github.com/veawho/via54Larkgroups/blob/main/docs/setup_zh.md).

Required OAuth scopes (only these 3):
- `im:message:readonly`
- `im:message.group_at_msg:readonly`
- `contact:user.base:readonly`

### Save credentials

```bash
feishu-vault config --app-id "cli_xxx" --app-secret "yyy"
```

### Login + sync

```bash
feishu-vault login      # opens browser
feishu-vault sync       # last 24h
feishu-vault archive    # export to Markdown
```

## Security Model

| Aspect | Guarantee |
|--------|-----------|
| **Data location** | All in `~/AppData/Local/hermes/feishu_vault/` |
| **Network targets** | Only `open.feishu.cn` + `passport.feishu.cn` |
| **OAuth scope** | Hardcoded allowlist (3 readonly scopes) |
| **Token TTL** | 24h hardcoded |
| **Default state** | OFF — manual sync unless opt-in |
| **Stop button** | `feishu-vault stop` within 5s |
| **Write capability** | NONE — tool cannot send messages |

## Links

- 📦 [GitHub repo](https://github.com/veawho/via54Larkgroups)
- 📖 [Full README](https://github.com/veawho/via54Larkgroups/blob/main/README.md)
- 🇨🇳 [中文使用手册](https://github.com/veawho/via54Larkgroups/blob/main/docs/setup_zh.md)
- 🏗️ [Architecture docs](https://github.com/veawho/via54Larkgroups/blob/main/docs/architecture.md)
- 🛡️ [Security policy](https://github.com/veawho/via54Larkgroups/blob/main/SECURITY.md)
- 📋 [Changelog](https://github.com/veawho/via54Larkgroups/blob/main/CHANGELOG.md)

## License

MIT — see [LICENSE](https://github.com/veawho/via54Larkgroups/blob/main/LICENSE).