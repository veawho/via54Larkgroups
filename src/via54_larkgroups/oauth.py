"""OAuth login flow for feishu-vault.

Browser-based OAuth user flow:
1. Generate PKCE verifier + challenge
2. Start a local HTTP server on a random port to receive callback
3. Open browser to Feishu authorize URL with scope=ALLOWED_SCOPES
4. User logs in + approves
5. Feishu redirects to localhost with ?code=xxx
6. Exchange code for user_access_token
7. Save token.json with expiry (TTL = 24h, enforced)

NEVER asks for offline_access scope. NEVER persists refresh_token beyond 24h.
"""
import http.server
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import Optional

from . import config


AUTHORIZE_URL = config.FEISHU_AUTH_BASE
TOKEN_URL = config.FEISHU_API_BASE + "/authen/v2/oauth/token"


def _gen_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    import hashlib
    import base64
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    return verifier, challenge


def login(app_id: str, app_secret: str, open_browser: bool = True,
          redirect_port: int = 0) -> dict:
    """Run the OAuth user flow. Returns the token dict on success.

    Args:
        app_id: Feishu app ID (cli_xxx)
        app_secret: Feishu app secret
        open_browser: if True, auto-opens browser
        redirect_port: 0 = pick random free port
    """
    config.ensure_dirs()

    # Pick a free port
    if redirect_port == 0:
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        redirect_port = s.getsockname()[1]
        s.close()

    redirect_uri = "http://127.0.0.1:" + str(redirect_port) + "/callback"

    verifier, challenge = _gen_pkce_pair()
    state = secrets.token_urlsafe(16)

    # Container for the auth code (filled by HTTP callback)
    received: dict = {"code": None, "error": None}
    event = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/callback":
                if "code" in qs:
                    received["code"] = qs["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<h2>feishu-vault: login successful</h2>"
                        b"<p>You can close this tab now.</p>"
                    )
                else:
                    received["error"] = qs.get("error", ["unknown"])[0]
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"login failed: " + received["error"].encode())
                event.set()
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args, **kwargs):
            return  # silence

    httpd = http.server.HTTPServer(("127.0.0.1", redirect_port), Handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # Build authorize URL
    scope_str = " ".join(config.ALLOWED_SCOPES)
    auth_url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": scope_str,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })

    print("[feishu-vault] Opening browser for Feishu login...")
    print("[feishu-vault] If browser does not open, visit:")
    print("    " + auth_url)
    if open_browser:
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            print("[feishu-vault] webbrowser.open failed: " + str(e))

    # Wait up to 5 minutes for user to complete login
    event.wait(timeout=300)
    httpd.shutdown()

    if received["error"]:
        raise RuntimeError("OAuth failed: " + received["error"])
    if not received["code"]:
        raise RuntimeError("OAuth timed out (no callback received in 5 min)")

    # Exchange code for token
    token_body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "code": received["code"],
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    # Validate scope returned
    returned_scope = token_data.get("scope", "")
    returned_scopes = set(returned_scope.split())
    extra = returned_scopes - config.SCOPE_ALLOWLIST
    if extra:
        raise RuntimeError(
            "Refusing token: server granted non-allowlisted scopes: " + str(extra)
        )

    # Force 24h cap
    now = int(time.time())
    token_data["issued_at"] = now
    token_data["expires_at"] = now + config.USER_TOKEN_TTL_SECONDS
    token_data["scope"] = " ".join(sorted(returned_scopes))  # normalize

    # Strip refresh_token if present (we don't use it)
    token_data.pop("refresh_token", None)

    # Save
    with open(config.TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    config.write_audit("oauth_login", scopes=list(returned_scopes), expires_at=token_data["expires_at"])
    return token_data


def load_token() -> Optional[dict]:
    """Load saved token. Returns None if expired or missing."""
    if not config.TOKEN_FILE.exists():
        return None
    try:
        with open(config.TOKEN_FILE, "r", encoding="utf-8") as f:
            token = json.load(f)
        expires_at = token.get("expires_at", 0)
        if int(time.time()) >= expires_at:
            config.write_audit("token_expired", expired_at=expires_at)
            return None
        return token
    except (json.JSONDecodeError, OSError):
        return None


def clear_token():
    if config.TOKEN_FILE.exists():
        config.TOKEN_FILE.unlink()
        config.write_audit("token_cleared")