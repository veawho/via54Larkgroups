# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [1.1.0] - 2026-06-29

- Add integrations/ for WhatsApp-Chat-Exporter, tg-archive, DiscordChatExporter. Plan multi-platform support.
## [1.0] - 2026-06-29

- Add architecture-comparison.md (vs WhatsApp-Chat-Exporter 1.1K, tg-archive 1.1K)
- Plan: static website output inspired by tg-archive

## [0.2.0] - 2026-06-24

### Changed
- **Renamed package** from `feishu_vault` to `via54_larkgroups` (matches GitHub repo name)
- CLI command stays `feishu-vault` for backward compatibility
- Updated internal imports throughout the package

### Added
- Full GitHub-standard project structure (`pyproject.toml`, `.gitignore`, `LICENSE`, etc.)
- Comprehensive test suite (`tests/`) using stdlib mocks — no network required
- GitHub Actions CI workflow (`.github/workflows/`)
- Issue templates (`.github/ISSUE_TEMPLATE/`)
- `requirements-dev.txt` for development dependencies
- `docs/` directory with setup guide and architecture docs

### Fixed
- `--enable-auto-sync` argparse conflict with subparser (handled manually before parse)
- `feishu-vault.bat` wrapper used wrong project root (fixed relative path resolution)

## [0.1.0] - 2026-06-24

### Added
- Initial release as `feishu-vault` (precursor name)
- OAuth browser-based login with PKCE
- Local SQLite storage (`vault.db`)
- Markdown export grouped by chat (`archive/YYYY-MM-DD/YYYY-MM-DD.md`)
- Attachment metadata + opt-in file download
- Audit log (`audit.log`) for every sync action
- 24h token TTL enforcement (hardcoded)
- Scope allowlist (3 read-only scopes, hardcoded)
- One-command stop (`feishu-vault stop`)
- Windows `.bat` wrapper