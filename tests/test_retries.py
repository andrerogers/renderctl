import base64
from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from renderctl.providers.openai_provider import OpenAIProvider

TINY_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
    0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
    0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
])


def _ok_resp():
    b64 = base64.b64encode(TINY_PNG).decode()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"images": [{"image_url": {"url": f"data:image/png;base64,{b64}"}}]}}]
    }
    return resp


def _err_resp(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"{status_code}", request=MagicMock(), response=MagicMock(status_code=status_code)
    )
    return resp


def test_succeeds_on_first_attempt(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = OpenAIProvider()
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()) as mock_post, \
         patch("renderctl.providers.base.time.sleep") as mock_sleep:
        provider.generate("test", tmp_path)
    mock_post.assert_called_once()
    mock_sleep.assert_not_called()


def test_retries_on_429_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = OpenAIProvider()
    with patch("renderctl.providers.base.httpx.post", side_effect=[_err_resp(429), _err_resp(429), _ok_resp()]) as mock_post, \
         patch("renderctl.providers.base.time.sleep") as mock_sleep:
        provider.generate("test", tmp_path)
    assert mock_post.call_count == 3
    assert mock_sleep.call_args_list == [call(1), call(2)]


def test_retries_on_500_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = OpenAIProvider()
    with patch("renderctl.providers.base.httpx.post", side_effect=[_err_resp(500), _ok_resp()]) as mock_post, \
         patch("renderctl.providers.base.time.sleep"):
        provider.generate("test", tmp_path)
    assert mock_post.call_count == 2


def test_no_retry_on_401(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = OpenAIProvider()
    with patch("renderctl.providers.base.httpx.post", return_value=_err_resp(401)) as mock_post, \
         patch("renderctl.providers.base.time.sleep") as mock_sleep:
        with pytest.raises(httpx.HTTPStatusError):
            provider.generate("test", tmp_path)
    mock_post.assert_called_once()
    mock_sleep.assert_not_called()


def test_all_retries_exhausted_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    provider = OpenAIProvider()
    with patch("renderctl.providers.base.httpx.post", return_value=_err_resp(503)) as mock_post, \
         patch("renderctl.providers.base.time.sleep"):
        with pytest.raises(httpx.HTTPStatusError):
            provider.generate("test", tmp_path)
    assert mock_post.call_count == 3
