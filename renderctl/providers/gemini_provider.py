import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from renderctl.models import GenerateResult

MODEL = "gemini-3.1-flash-image-preview"


class GeminiProvider:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str, output_dir: Path) -> GenerateResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        response = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        elapsed_ms = int((time.time() - start) * 1000)

        image_data = response.candidates[0].content.parts[0].inline_data.data

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        stem = f"{ts}_gemini_{prompt_hash}"
        file_path = output_dir / f"{stem}.png"
        sidecar_path = output_dir / f"{stem}.json"

        file_path.write_bytes(image_data)
        sidecar_path.write_text(json.dumps({
            "prompt": prompt,
            "provider": "gemini",
            "model": MODEL,
            "created_at": datetime.now().isoformat(),
            "generation_time_ms": elapsed_ms,
        }, indent=2))

        return GenerateResult(
            file_path=str(file_path),
            provider="gemini",
            model=MODEL,
            generation_time_ms=elapsed_ms,
        )

    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult:
        raise NotImplementedError("edit is not supported by the gemini provider")
