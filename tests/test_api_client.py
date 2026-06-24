"""Tests for via54_larkgroups.api_client.

Mock-based tests for HTTP error handling, no real network.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from via54_larkgroups.api_client import FeishuClient, FeishuAPIError


class TestFeishuAPIError:
    def test_construction(self):
        e = FeishuAPIError(400, "bad request", {"detail": "x"})
        assert e.code == 400
        assert e.msg == "bad request"
        assert "400" in str(e)


class TestFeishuClient:
    def _mock_response(self, status, body):
        """Create a mock response object."""
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode("utf-8")
        resp.status = status
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_request_success(self):
        client = FeishuClient("fake_token")
        mock_resp = self._mock_response(200, {"code": 0, "msg": "success", "data": {"foo": "bar"}})
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client._request("GET", "/test")
        assert result == {"foo": "bar"}

    def test_request_api_error_code(self):
        """Non-zero code in Feishu envelope should raise FeishuAPIError."""
        client = FeishuClient("fake_token")
        mock_resp = self._mock_response(200, {"code": 99991663, "msg": "token invalid"})
        # urllib doesn't raise on HTTP 200; we check body
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(FeishuAPIError) as exc:
                client._request("GET", "/test")
        assert exc.value.code == 99991663

    def test_request_http_error(self):
        """HTTP 4xx/5xx raises HTTPError → we convert to FeishuAPIError."""
        client = FeishuClient("fake_token")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "code": 401, "msg": "Unauthorized"
        }).encode("utf-8")
        http_err = urllib.error.HTTPError(
            "http://test", 401, "Unauthorized", {}, mock_resp
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(FeishuAPIError) as exc:
                client._request("GET", "/test")
        assert exc.value.code == 401

    def test_authorization_header(self):
        """Bearer token must be in Authorization header."""
        client = FeishuClient("my_test_token")
        captured = {}

        def fake_urlopen(req, **kwargs):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.headers)
            resp = MagicMock()
            resp.read.return_value = json.dumps({
                "code": 0, "msg": "ok", "data": {}
            }).encode("utf-8")
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client._request("GET", "/test")
        assert captured["headers"]["Authorization"] == "Bearer my_test_token"