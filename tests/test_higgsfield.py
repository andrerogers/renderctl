import json
from unittest.mock import MagicMock, patch, call

import pytest
from typer.testing import CliRunner

from renderctl.cli import app
from renderctl.providers.higgsfield_provider import HiggsFieldProvider
from renderctl.providers.base import SafetyRefusalError

runner = CliRunner()

TINY_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
    0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
    0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
])


def _submit_resp(request_id="req_abc"):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"request_id": request_id, "status_url": f"/requests/{request_id}/status"}
    return resp


def _poll_resp(status, image_url=None):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    data = {"status": status}
    if status == "completed":
        data["images"] = [{"url": image_url or "https://example.com/out.png"}]
    resp.json.return_value = data
    return resp


def _image_resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.content = TINY_PNG
    return resp


def test_higgsfield_generate(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()

    with patch("renderctl.providers.higgsfield_provider.httpx.post", return_value=_submit_resp()) as mock_post, \
         patch("renderctl.providers.higgsfield_provider.httpx.get", side_effect=[_poll_resp("completed"), _image_resp()]) as mock_get, \
         patch("renderctl.providers.higgsfield_provider.time.sleep"):
        result = provider.generate("a red panda", tmp_path)

    assert result.provider == "higgsfield"
    assert result.model == "bytedance/seedream/v4/text-to-image"
    assert result.status == "success"
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].read_bytes() == TINY_PNG


def test_higgsfield_polls_until_completed(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()

    with patch("renderctl.providers.higgsfield_provider.httpx.post", return_value=_submit_resp()), \
         patch("renderctl.providers.higgsfield_provider.httpx.get", side_effect=[
             _poll_resp("queued"),
             _poll_resp("in_progress"),
             _poll_resp("completed"),
             _image_resp(),
         ]) as mock_get, \
         patch("renderctl.providers.higgsfield_provider.time.sleep"):
        provider.generate("test", tmp_path)

    assert mock_get.call_count == 4  # 3 polls + 1 image download


def test_higgsfield_nsfw_raises_safety_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()

    with patch("renderctl.providers.higgsfield_provider.httpx.post", return_value=_submit_resp()), \
         patch("renderctl.providers.higgsfield_provider.httpx.get", return_value=_poll_resp("nsfw")), \
         patch("renderctl.providers.higgsfield_provider.time.sleep"):
        with pytest.raises(SafetyRefusalError):
            provider.generate("bad prompt", tmp_path)


def test_higgsfield_failed_raises_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()

    with patch("renderctl.providers.higgsfield_provider.httpx.post", return_value=_submit_resp()), \
         patch("renderctl.providers.higgsfield_provider.httpx.get", return_value=_poll_resp("failed")), \
         patch("renderctl.providers.higgsfield_provider.time.sleep"):
        with pytest.raises(RuntimeError):
            provider.generate("test", tmp_path)


def test_higgsfield_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("HIGGSFIELD_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--provider", "higgsfield", "--output-dir", str(tmp_path)])
    assert result.exit_code == 3


def test_higgsfield_edit_unsupported(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()
    png = tmp_path / "in.png"
    png.write_bytes(TINY_PNG)
    with pytest.raises(NotImplementedError):
        provider.edit(png, "make it blue", tmp_path)


def test_higgsfield_sidecar_written(tmp_path, monkeypatch):
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "test-key")
    provider = HiggsFieldProvider()

    with patch("renderctl.providers.higgsfield_provider.httpx.post", return_value=_submit_resp()), \
         patch("renderctl.providers.higgsfield_provider.httpx.get", side_effect=[_poll_resp("completed"), _image_resp()]), \
         patch("renderctl.providers.higgsfield_provider.time.sleep"):
        result = provider.generate("a test", tmp_path)

    sidecars = list(tmp_path.glob("*.json"))
    assert len(sidecars) == 1
    meta = json.loads(sidecars[0].read_text())
    assert meta["provider"] == "higgsfield"
    assert meta["prompt"] == "a test"
