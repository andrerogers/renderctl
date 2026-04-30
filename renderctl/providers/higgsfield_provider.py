import os
import time
from pathlib import Path

import httpx

from renderctl.models import GenerateResult
from renderctl.providers.base import BaseProvider, SafetyRefusalError

_BASE = "https://platform.higgsfield.ai"
_POLL_INTERVAL = 3
_POLL_TIMEOUT = 300


class HiggsFieldProvider(BaseProvider):
    MODEL = "bytedance/seedream/v4/text-to-image"
    PROVIDER_NAME = "higgsfield"

    def __init__(self) -> None:
        api_key = os.environ.get("HIGGSFIELD_API_KEY")
        if not api_key:
            raise ValueError("HIGGSFIELD_API_KEY not set")
        self._hf_headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, output_dir: Path) -> GenerateResult:
        start = time.monotonic()
        resp = httpx.post(
            f"{_BASE}/{self.MODEL}",
            headers=self._hf_headers,
            json={"prompt": prompt, "resolution": "1K", "aspect_ratio": "1:1"},
            timeout=30,
        )
        resp.raise_for_status()
        request_id = resp.json()["request_id"]

        deadline = time.monotonic() + _POLL_TIMEOUT
        image_url = None
        while time.monotonic() < deadline:
            time.sleep(_POLL_INTERVAL)
            poll = httpx.get(
                f"{_BASE}/requests/{request_id}/status",
                headers=self._hf_headers,
                timeout=30,
            )
            poll.raise_for_status()
            result = poll.json()
            status = result.get("status")
            if status == "completed":
                image_url = result["images"][0]["url"]
                break
            if status in ("failed", "canceled"):
                raise RuntimeError(f"generation {status}: {result.get('error', '')}")
            if status == "nsfw":
                raise SafetyRefusalError("content flagged as NSFW by Higgsfield")

        if image_url is None:
            raise TimeoutError(f"generation did not complete within {_POLL_TIMEOUT}s")

        img_resp = httpx.get(image_url, timeout=60)
        img_resp.raise_for_status()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        file_path, created_at = self._save(
            img_resp.content, prompt, output_dir, {"generation_time_ms": elapsed_ms}
        )
        return GenerateResult(
            file_path=str(file_path),
            provider=self.PROVIDER_NAME,
            model=self.MODEL,
            generation_time_ms=elapsed_ms,
            created_at=created_at,
        )

    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult:
        raise NotImplementedError("edit is not supported by the higgsfield provider")
