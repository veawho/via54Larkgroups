"""Feishu Open API client (stdlib only: urllib + json).

Used by sync.py and oauth.py. Never logs or sends tokens to anywhere except Feishu API.
"""
import json
import urllib.request
import urllib.error

from . import config


class FeishuAPIError(Exception):
    def __init__(self, code: int, msg: str, response: dict = None):
        self.code = code
        self.msg = msg
        self.response = response or {}
        super().__init__(f"Feishu API error {code}: {msg}")


class FeishuClient:
    def __init__(self, user_access_token: str):
        self.token = user_access_token

    def _request(self, method: str, path: str, body: dict = None, query: dict = None) -> dict:
        url = config.FEISHU_API_BASE + path
        if query:
            from urllib.parse import urlencode
            url += "?" + urlencode(query)
        data = None
        headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json; charset=utf-8",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(err_body)
            except Exception:
                payload = {"code": e.code, "msg": err_body}
            raise FeishuAPIError(payload.get("code", e.code), payload.get("msg", str(e)), payload)
        except urllib.error.URLError as e:
            raise FeishuAPIError(-1, str(e))
        # Feishu wraps everything in {"code": 0, "msg": "success", "data": {...}}
        if payload.get("code") != 0:
            raise FeishuAPIError(payload.get("code", -1), payload.get("msg", "unknown"), payload)
        return payload.get("data", {})

    # === Message APIs ===
    def list_chats(self, page_size: int = 50) -> dict:
        """List all chats user is in (DMs + groups)."""
        return self._request("GET", "/im/v1/chats", query={"page_size": page_size})

    def list_messages(self, chat_id: str, start_time: str = None, end_time: str = None,
                      page_size: int = 50) -> dict:
        """List messages in a chat. Times are ISO 8601 strings."""
        query = {"chat_id": chat_id, "page_size": page_size}
        if start_time:
            query["start_time"] = start_time
        if end_time:
            query["end_time"] = end_time
        return self._request("GET", "/im/v1/messages", query=query)

    def get_message(self, message_id: str) -> dict:
        return self._request("GET", "/im/v1/messages/" + message_id)

    def get_message_resource(self, message_id: str, file_key: str, type_: str = "file") -> dict:
        """Get download URL for an attachment."""
        return self._request(
            "GET",
            "/im/v1/messages/" + message_id + "/resources/" + file_key,
            query={"type": type_},
        )

    # === User APIs ===
    def get_current_user(self) -> dict:
        return self._request("GET", "/authen/v1/user_info")