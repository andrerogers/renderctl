import base64
import hashlib
import json
import os
import secrets
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from renderctl.models import GenerateResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class SafetyRefusalError(Exception):
    pass


class BaseProvider(ABC):
    MODEL: str
    PROVIDER_NAME: str

    def __init__(self) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, messages: list[dict[str, Any]]) -> tuple[bytes, int]:
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "modalities": ["image", "text"],
        }
        start = time.monotonic()
        resp = httpx.post(OPENROUTER_URL, headers=self._headers, json=payload, timeout=120)
        resp.raise_for_status()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()
        images = data["choices"][0]["message"].get("images")
        if not images:
            content = data["choices"][0]["message"].get("content", "")
            raise SafetyRefusalError(content or "request refused by provider")
        image_url = images[0]["image_url"]["url"]
        return self._decode_image(image_url), elapsed_ms

    def _decode_image(self, url: str) -> bytes:
        if not url.startswith("data:"):
            raise ValueError(f"unexpected image URL scheme: {url[:50]!r}")
        _, b64 = url.split(",", 1)
        return base64.b64decode(b64)

    def _save(self, image_data: bytes, prompt: str, output_dir: Path, extra: dict[str, Any]) -> tuple[Path, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S_%f")
        stem = f"{ts}_{self.PROVIDER_NAME}_{hashlib.sha256(prompt.encode()).hexdigest()[:8]}_{secrets.token_hex(2)}"
        file_path = output_dir / f"{stem}.png"
        created_at = now.isoformat()
        file_path.write_bytes(image_data)
        (output_dir / f"{stem}.json").write_text(
            json.dumps({
                "prompt": prompt,
                "provider": self.PROVIDER_NAME,
                "model": self.MODEL,
                "created_at": created_at,
                **extra,
            }, indent=2),
            encoding="utf-8",
        )
        return file_path, created_at

    def generate(self, prompt: str, output_dir: Path) -> GenerateResult:
        messages = [{"role": "user", "content": prompt}]
        image_data, elapsed_ms = self._post(messages)
        file_path, created_at = self._save(image_data, prompt, output_dir, {"generation_time_ms": elapsed_ms})
        return GenerateResult(
            file_path=str(file_path),
            provider=self.PROVIDER_NAME,
            model=self.MODEL,
            generation_time_ms=elapsed_ms,
            created_at=created_at,
        )

    @abstractmethod
    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult: ...
