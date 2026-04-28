import base64
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import openai

from renderctl.models import GenerateResult

MODEL = "gpt-image-2"


class OpenAIProvider:
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.client = openai.OpenAI(api_key=api_key)

    def generate(self, prompt: str, output_dir: Path) -> GenerateResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        response = self.client.images.generate(
            model=MODEL,
            prompt=prompt,
            n=1,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        image_data = base64.b64decode(response.data[0].b64_json)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        stem = f"{ts}_openai_{prompt_hash}"
        file_path = output_dir / f"{stem}.png"
        sidecar_path = output_dir / f"{stem}.json"

        file_path.write_bytes(image_data)
        sidecar_path.write_text(json.dumps({
            "prompt": prompt,
            "provider": "openai",
            "model": MODEL,
            "created_at": datetime.now().isoformat(),
            "generation_time_ms": elapsed_ms,
        }, indent=2))

        return GenerateResult(
            file_path=str(file_path),
            provider="openai",
            model=MODEL,
            generation_time_ms=elapsed_ms,
        )

    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        with open(input_file, "rb") as f:
            response = self.client.images.edit(
                model=MODEL,
                image=f,
                prompt=prompt,
            )
        elapsed_ms = int((time.time() - start) * 1000)

        image_data = base64.b64decode(response.data[0].b64_json)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        stem = f"{ts}_openai_{prompt_hash}"
        file_path = output_dir / f"{stem}.png"
        sidecar_path = output_dir / f"{stem}.json"

        file_path.write_bytes(image_data)
        sidecar_path.write_text(json.dumps({
            "prompt": prompt,
            "provider": "openai",
            "model": MODEL,
            "operation": "edit",
            "input_file": str(input_file),
            "created_at": datetime.now().isoformat(),
            "generation_time_ms": elapsed_ms,
        }, indent=2))

        return GenerateResult(
            file_path=str(file_path),
            provider="openai",
            model=MODEL,
            generation_time_ms=elapsed_ms,
        )
