import base64
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from renderctl.cli import app

runner = CliRunner()

TINY_PNG_BYTES = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
    0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
    0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
])


def mock_openrouter_response(image_bytes: bytes) -> MagicMock:
    b64 = base64.b64encode(image_bytes).decode()
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"images": [{"image_url": {"url": f"data:image/png;base64,{b64}"}}]}}]
    }
    return resp


def mock_refusal_response() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": "I cannot edit that image."}}]
    }
    return resp


def test_edit_creates_image_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG_BYTES)
    out_dir = tmp_path / "out"

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, [
            "edit", str(input_png), "make it cyberpunk",
            "--output-dir", str(out_dir),
        ])

    assert result.exit_code == 0
    pngs = list(out_dir.glob("*.png"))
    assert len(pngs) == 1

    sidecars = list(out_dir.glob("*.json"))
    assert len(sidecars) == 1
    sidecar = json.loads(sidecars[0].read_text())
    assert sidecar["prompt"] == "make it cyberpunk"
    assert sidecar["operation"] == "edit"
    assert sidecar["provider"] == "openai"
    assert "created_at" in sidecar


def test_edit_json_output(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG_BYTES)

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, [
            "edit", str(input_png), "make it cyberpunk",
            "--output-dir", str(tmp_path), "--json",
        ])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["provider"] == "openai"
    assert "created_at" in data


def test_edit_missing_input_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    result = runner.invoke(app, [
        "edit", str(tmp_path / "nonexistent.png"), "prompt",
        "--output-dir", str(tmp_path),
    ])
    assert result.exit_code == 2


def test_edit_gemini_unsupported(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG_BYTES)

    result = runner.invoke(app, [
        "edit", str(input_png), "make it cyberpunk",
        "--provider", "gemini", "--output-dir", str(tmp_path),
    ])

    assert result.exit_code == 2


def test_edit_safety_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG_BYTES)

    with patch("renderctl.providers.base.httpx.post", return_value=mock_refusal_response()):
        result = runner.invoke(app, [
            "edit", str(input_png), "make it cyberpunk",
            "--output-dir", str(tmp_path),
        ])

    assert result.exit_code == 5


def test_edit_json_error_is_json(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG_BYTES)

    with patch("renderctl.providers.base.httpx.post", return_value=mock_refusal_response()):
        result = runner.invoke(app, [
            "edit", str(input_png), "bad prompt",
            "--output-dir", str(tmp_path), "--json",
        ])

    assert result.exit_code == 5
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["status"] == "error"
