---
name: Pull request
about: Submit a code change
title: '[PR] '
labels: ''
---

## What does this PR do?

## Why?

## Related issues

Closes #

## Security check

- [ ] No new network destinations added (only `*.feishu.cn` allowed)
- [ ] No new OAuth scopes requested (must be in `ALLOWED_SCOPES` allowlist)
- [ ] Does not change default state from OFF to ON
- [ ] Does not affect token expiry handling
- [ ] All new code paths are tested

## Testing

- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes

## Screenshots / output

If applicable.