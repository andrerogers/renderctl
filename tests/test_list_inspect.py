import json
from pathlib import Path

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

SAMPLE_SIDECAR = {
    "prompt": "a futuristic city",
    "provider": "openai",
    "model": "gpt-image-2",
    "created_at": "2026-04-28T12:00:00",
    "generation_time_ms": 1234,
}


def make_image(directory: Path, name: str, sidecar: dict = None) -> Path:
    png = directory / f"{name}.png"
    png.write_bytes(TINY_PNG_BYTES)
    if sidecar is not None:
        (directory / f"{name}.json").write_text(json.dumps(sidecar))
    return png


# --- list ---

def test_list_empty_dir(tmp_path):
    result = runner.invoke(app, ["list", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No images found" in result.output


def test_list_with_images(tmp_path):
    make_image(tmp_path, "img1", SAMPLE_SIDECAR)
    make_image(tmp_path, "img2", {**SAMPLE_SIDECAR, "prompt": "a sunset"})

    result = runner.invoke(app, ["list", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "a futuristic city" in result.output
    assert "a sunset" in result.output


def test_list_json_output(tmp_path):
    make_image(tmp_path, "img1", SAMPLE_SIDECAR)

    result = runner.invoke(app, ["list", "--output-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["prompt"] == "a futuristic city"
    assert "file_path" in data[0]


def test_list_image_without_sidecar(tmp_path):
    make_image(tmp_path, "img1", sidecar=None)

    result = runner.invoke(app, ["list", "--output-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0] == {"file_path": str(tmp_path / "img1.png")}


def test_list_missing_dir(tmp_path):
    result = runner.invoke(app, ["list", "--output-dir", str(tmp_path / "nonexistent")])
    assert result.exit_code == 6


# --- inspect ---

def test_inspect_prints_sidecar(tmp_path):
    png = make_image(tmp_path, "img1", SAMPLE_SIDECAR)

    result = runner.invoke(app, ["inspect", str(png)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["prompt"] == "a futuristic city"
    assert data["provider"] == "openai"


def test_inspect_missing_sidecar(tmp_path):
    png = make_image(tmp_path, "img1", sidecar=None)

    result = runner.invoke(app, ["inspect", str(png)])
    assert result.exit_code == 1


def test_inspect_missing_file(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "ghost.png")])
    assert result.exit_code == 2
