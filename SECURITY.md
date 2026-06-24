# Security Policy

## Threat Model

This tool handles sensitive personal data (your private chats). The threat model assumes:

- **Adversary:** A malicious actor who has local disk access OR who can intercept network traffic
- **NOT in scope:** A malicious actor who has compromised your OS / browser / Feishu account itself

## Security Guarantees

### 1. Local-only data
- All data stored at `~/AppData/Local/hermes/feishu_vault/`
- No upload to any third-party server
- Only network targets: `open.feishu.cn` and `passport.feishu.cn`

### 2. Minimum OAuth scope
Hardcoded allowlist (in `src/via54_larkgroups/config.py`):
```python
ALLOWED_SCOPES = [
    "im:message:readonly",
    "im:message.group_at_msg:readonly",
    "contact:user.base:readonly",
]
```
The tool will **refuse to save** a token that includes any scope outside this list.

### 3. Token TTL
- Maximum 24 hours (hardcoded `USER_TOKEN_TTL_SECONDS = 24 * 3600`)
- Tokens are checked on every command run
- Expired tokens force re-login

### 4. Default state
- All sync / archive operations are manual
- Auto-sync requires explicit `--enable-auto-sync`
- The `stop` command halts background processes within 5 seconds

### 5. Audit trail
Every sync writes a JSON entry to `audit.log`:
```json
{"ts": "...", "action": "sync_complete", "messages": 142, "bytes_text": 18432, ...}
```

## Reporting a Vulnerability

**Do NOT file public GitHub issues for security vulnerabilities.**

Email: [create a GitHub Security Advisory](https://github.com/via54/via54Larkgroups/security/advisories/new) (private channel).

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

Response time: best-effort, within 7 days.

## What counts as a vulnerability

✅ Report these:
- Any code path that sends data to a non-Feishu server
- Any way to bypass the 24h token expiry
- Any way to request OAuth scopes outside the allowlist
- Any path that grants the tool write/send capabilities
- Any code that logs tokens or secrets to disk without encryption

❌ Not vulnerabilities (but still file as bugs):
- UI/UX issues
- Missing features
- Documentation gaps

## Verify yourself

```bash
# Check no unexpected network destinations
grep -rn "https://" src/ | grep -v "feishu.cn"

# Check no write scopes in source
grep -rn "im:message:send\|im:message:" src/ | grep -v "readonly"

# Check audit log integrity
tail -f ~/AppData/Local/hermes/feishu_vault/audit.log
```

If any of these produce unexpected output, **stop using the tool** and file an advisory.