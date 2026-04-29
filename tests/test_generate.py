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
        "choices": [{"message": {"content": "I cannot generate that image."}}]
    }
    return resp


def test_generate_creates_image_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, ["generate", "a test prompt", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].read_bytes() == TINY_PNG_BYTES

    sidecars = list(tmp_path.glob("*.json"))
    assert len(sidecars) == 1
    sidecar = json.loads(sidecars[0].read_text())
    assert sidecar["prompt"] == "a test prompt"
    assert sidecar["provider"] == "openai"
    assert sidecar["model"] == "openai/gpt-5.4-image-2"
    assert "created_at" in sidecar


def test_generate_json_output(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, ["generate", "a test prompt", "--output-dir", str(tmp_path), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["status"] == "success"
    assert data["provider"] == "openai"
    assert data["model"] == "openai/gpt-5.4-image-2"
    assert "created_at" in data


def test_generate_prompt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("a futuristic city at sunset")

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, [
            "generate", "--prompt-file", str(prompt_file), "--output-dir", str(tmp_path)
        ])

    assert result.exit_code == 0


def test_generate_missing_prompt(tmp_path):
    result = runner.invoke(app, ["generate", "--output-dir", str(tmp_path)])
    assert result.exit_code == 2


def test_generate_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--output-dir", str(tmp_path)])
    assert result.exit_code == 3


def test_gemini_generate_creates_image_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, [
            "generate", "a test prompt", "--provider", "gemini", "--output-dir", str(tmp_path)
        ])

    assert result.exit_code == 0
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].read_bytes() == TINY_PNG_BYTES

    sidecars = list(tmp_path.glob("*.json"))
    assert len(sidecars) == 1
    sidecar = json.loads(sidecars[0].read_text())
    assert sidecar["prompt"] == "a test prompt"
    assert sidecar["provider"] == "gemini"
    assert sidecar["model"] == "google/gemini-3.1-flash-image-preview"


def test_gemini_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--provider", "gemini", "--output-dir", str(tmp_path)])
    assert result.exit_code == 3


def test_unknown_provider(tmp_path):
    result = runner.invoke(app, ["generate", "test", "--provider", "unknown", "--output-dir", str(tmp_path)])
    assert result.exit_code == 2


def test_generate_prompt_and_file_are_mutually_exclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("hello")
    result = runner.invoke(app, [
        "generate", "inline prompt", "--prompt-file", str(prompt_file), "--output-dir", str(tmp_path)
    ])
    assert result.exit_code == 2


def test_generate_empty_prompt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    prompt_file = tmp_path / "empty.txt"
    prompt_file.write_text("   \n  ")
    result = runner.invoke(app, [
        "generate", "--prompt-file", str(prompt_file), "--output-dir", str(tmp_path)
    ])
    assert result.exit_code == 2


def test_generate_provider_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        result = runner.invoke(app, [
            "generate", "a test prompt", "--provider", "OpenAI", "--output-dir", str(tmp_path)
        ])
    assert result.exit_code == 0


def test_generate_safety_refusal(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("renderctl.providers.base.httpx.post", return_value=mock_refusal_response()):
        result = runner.invoke(app, ["generate", "bad prompt", "--output-dir", str(tmp_path)])
    assert result.exit_code == 5


def test_generate_json_error_is_json(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--output-dir", str(tmp_path), "--json"])
    assert result.exit_code == 3
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["status"] == "error"
    assert "error_message" in data


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "renderctl" in result.output


def test_generate_no_collision_same_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("renderctl.providers.base.httpx.post", return_value=mock_openrouter_response(TINY_PNG_BYTES)):
        runner.invoke(app, ["generate", "same prompt", "--output-dir", str(tmp_path)])
        runner.invoke(app, ["generate", "same prompt", "--output-dir", str(tmp_path)])
    assert len(list(tmp_path.glob("*.png"))) == 2
