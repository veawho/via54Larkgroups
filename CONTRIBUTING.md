# Contributing to via54Larkgroups

Thanks for your interest in contributing! This is a personal-scale project with a clear scope: **local-only Feishu chat archival for personal use**.

## Philosophy

Before contributing, please understand:

1. **Local-only is sacred.** Any PR that adds a network destination other than `open.feishu.cn` / `passport.feishu.cn` will be rejected.
2. **Opt-in by default.** Auto-sync, file downloads, anything "always on" must require explicit user action to enable.
3. **Stdlib preferred.** The project intentionally avoids third-party dependencies for the runtime. Tests can use `pytest`.
4. **No write capability.** The tool MUST NOT be able to send messages. Adding `im:message:send` scope is grounds for rejection.

## Setup

```bash
git clone https://github.com/via54/via54Larkgroups.git
cd via54Larkgroups
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

Tests use stdlib mocks — no network calls, no Feishu account needed.

## Code style

- Python 3.11+ syntax (use `dict[str, int]`, not `Dict[str, int]`)
- Line length: 100
- Formatter: `ruff format`
- Linter: `ruff check`

```bash
ruff format .
ruff check .
```

## Pull request process

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Write tests for new behavior (where applicable — UI-only changes may skip)
4. Ensure `pytest` passes
5. Ensure `ruff` passes
6. Update CHANGELOG.md under "Unreleased"
7. Open PR with a clear description of what and why

## Reporting bugs

Use the GitHub issue template. Include:
- OS + Python version
- `feishu-vault status` output (redact any token info!)
- Steps to reproduce
- Expected vs actual behavior

## Security issues

**Do NOT open public GitHub issues for security bugs.** See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.