import base64
import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from renderctl.cli import app

runner = CliRunner()

# Minimal valid 1x1 PNG
TINY_PNG_BYTES = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
    0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
    0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
])
TINY_PNG_B64 = base64.b64encode(TINY_PNG_BYTES).decode()


def mock_gemini_client(image_bytes: bytes) -> MagicMock:
    client = MagicMock()
    client.models.generate_images.return_value = MagicMock(
        generated_images=[MagicMock(image=MagicMock(image_bytes=image_bytes))]
    )
    return client


def mock_openai_client(b64_data: str) -> MagicMock:
    client = MagicMock()
    client.images.generate.return_value = MagicMock(
        data=[MagicMock(b64_json=b64_data)]
    )
    return client


def test_generate_creates_image_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("renderctl.providers.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value = mock_openai_client(TINY_PNG_B64)
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
    assert sidecar["model"] == "gpt-image-2"


def test_generate_json_output(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("renderctl.providers.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value = mock_openai_client(TINY_PNG_B64)
        result = runner.invoke(app, ["generate", "a test prompt", "--output-dir", str(tmp_path), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["status"] == "success"
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-image-2"


def test_generate_prompt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("a futuristic city at sunset")

    with patch("renderctl.providers.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value = mock_openai_client(TINY_PNG_B64)
        result = runner.invoke(app, [
            "generate", "--prompt-file", str(prompt_file), "--output-dir", str(tmp_path)
        ])

    assert result.exit_code == 0


def test_generate_missing_prompt(tmp_path):
    result = runner.invoke(app, ["generate", "--output-dir", str(tmp_path)])
    assert result.exit_code == 2


def test_generate_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--output-dir", str(tmp_path)])
    assert result.exit_code == 3


def test_gemini_generate_creates_image_and_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("renderctl.providers.gemini_provider.genai.Client") as mock_cls:
        mock_cls.return_value = mock_gemini_client(TINY_PNG_BYTES)
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


def test_gemini_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "test", "--provider", "gemini", "--output-dir", str(tmp_path)])
    assert result.exit_code == 3


def test_unknown_provider(tmp_path):
    result = runner.invoke(app, ["generate", "test", "--provider", "unknown", "--output-dir", str(tmp_path)])
    assert result.exit_code == 2


def test_generate_prompt_and_file_are_mutually_exclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    prompt_file = tmp_path / "p.txt"
    prompt_file.write_text("hello")
    result = runner.invoke(app, [
        "generate", "inline prompt", "--prompt-file", str(prompt_file), "--output-dir", str(tmp_path)
    ])
    assert result.exit_code == 2
