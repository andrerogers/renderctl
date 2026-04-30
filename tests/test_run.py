import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from renderctl.cli import app

runner = CliRunner()

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


def _write_job(tmp_path, jobs):
    job_file = tmp_path / "jobs.json"
    job_file.write_text(json.dumps(jobs))
    return job_file


def test_run_single_generate(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    job_file = _write_job(tmp_path, {
        "operation": "generate",
        "provider": "openai",
        "prompt": "a red panda",
        "output_dir": str(tmp_path),
    })
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()):
        result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 0
    assert len(list(tmp_path.glob("*.png"))) == 1


def test_run_batch_generate(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    job_file = _write_job(tmp_path, [
        {"operation": "generate", "provider": "openai", "prompt": "first", "output_dir": str(tmp_path)},
        {"operation": "generate", "provider": "openai", "prompt": "second", "output_dir": str(tmp_path)},
    ])
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()):
        result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 0
    assert len(list(tmp_path.glob("*.png"))) == 2


def test_run_json_output(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    job_file = _write_job(tmp_path, [
        {"operation": "generate", "provider": "openai", "prompt": "first", "output_dir": str(tmp_path)},
        {"operation": "generate", "provider": "openai", "prompt": "second", "output_dir": str(tmp_path)},
    ])
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()):
        result = runner.invoke(app, ["run", str(job_file), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["schema_version"] == "1.0"
    assert data[0]["status"] == "success"
    assert data[1]["provider"] == "openai"


def test_run_missing_job_file(tmp_path):
    result = runner.invoke(app, ["run", str(tmp_path / "nonexistent.json")])
    assert result.exit_code == 2


def test_run_invalid_json(tmp_path):
    job_file = tmp_path / "bad.json"
    job_file.write_text("{not valid json")
    result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 2


def test_run_missing_output_dir_field(tmp_path):
    job_file = _write_job(tmp_path, {"operation": "generate", "prompt": "test"})
    result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 2


def test_run_unsupported_operation(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    job_file = _write_job(tmp_path, {
        "operation": "inpaint",
        "provider": "openai",
        "prompt": "test",
        "output_dir": str(tmp_path),
    })
    result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 2


def test_run_missing_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    job_file = _write_job(tmp_path, {
        "operation": "generate",
        "provider": "openai",
        "output_dir": str(tmp_path),
    })
    result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 2


def test_run_edit_job(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    input_png = tmp_path / "input.png"
    input_png.write_bytes(TINY_PNG)
    job_file = _write_job(tmp_path, {
        "operation": "edit",
        "provider": "openai",
        "prompt": "make it cyberpunk",
        "input_file": str(input_png),
        "output_dir": str(tmp_path),
    })
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()):
        result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 0
    assert len(list(tmp_path.glob("*.png"))) == 2  # input + output


def test_run_prompt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    pf = tmp_path / "prompt.txt"
    pf.write_text("a test prompt")
    job_file = _write_job(tmp_path, {
        "operation": "generate",
        "provider": "openai",
        "prompt_file": str(pf),
        "output_dir": str(tmp_path),
    })
    with patch("renderctl.providers.base.httpx.post", return_value=_ok_resp()):
        result = runner.invoke(app, ["run", str(job_file)])
    assert result.exit_code == 0
