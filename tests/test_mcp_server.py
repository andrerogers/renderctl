import json
from unittest.mock import MagicMock, patch

import pytest

from renderctl.mcp_server import SCHEMA_VERSION, _run


def make_proc(stdout: str, stderr: str = "", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


SUCCESS_RESULT = {
    "schema_version": "1.0",
    "status": "success",
    "file_path": "/tmp/out.png",
    "provider": "openai",
    "model": "openai/gpt-5.4-image-2",
    "generation_time_ms": 1234,
    "created_at": "2026-04-28T12:00:00",
}


def test_run_success():
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(SUCCESS_RESULT))):
        result = _run(["generate", "a prompt", "--output-dir", "/tmp"])
    assert result["file_path"] == "/tmp/out.png"
    assert result["status"] == "success"


def test_run_error_propagates():
    error_payload = {"schema_version": "1.0", "status": "error", "error_message": "OPENROUTER_API_KEY not set"}
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(error_payload), returncode=3)):
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY not set"):
            _run(["generate", "a prompt", "--output-dir", "/tmp"])


def test_run_schema_version_mismatch():
    bad_version = {**SUCCESS_RESULT, "schema_version": "99.0"}
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(bad_version))):
        with pytest.raises(RuntimeError, match="schema version mismatch"):
            _run(["generate", "a prompt", "--output-dir", "/tmp"])


def test_run_empty_stdout_surfaces_stderr():
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc("", stderr="something crashed", returncode=1)):
        with pytest.raises(RuntimeError, match="something crashed"):
            _run(["generate", "a prompt", "--output-dir", "/tmp"])


def test_run_empty_stdout_no_stderr():
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc("", returncode=1)):
        with pytest.raises(RuntimeError, match="exited 1"):
            _run(["generate", "a prompt", "--output-dir", "/tmp"])


def test_run_list_returns_list():
    data = [{"file_path": "/tmp/a.png"}, {"file_path": "/tmp/b.png"}]
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(data))):
        result = _run(["list", "--output-dir", "/tmp"])
    assert isinstance(result, list)
    assert len(result) == 2


def test_run_passes_json_flag():
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(SUCCESS_RESULT))) as mock_run:
        _run(["generate", "a prompt", "--output-dir", "/tmp"])
    args = mock_run.call_args[0][0]
    assert "--json" in args


def test_run_uses_current_interpreter():
    import sys
    with patch("renderctl.mcp_server.subprocess.run", return_value=make_proc(json.dumps(SUCCESS_RESULT))) as mock_run:
        _run(["generate", "a prompt", "--output-dir", "/tmp"])
    args = mock_run.call_args[0][0]
    assert args[0] == sys.executable
    assert args[1:3] == ["-m", "renderctl"]
