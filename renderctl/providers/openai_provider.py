import base64
from pathlib import Path

from renderctl.models import GenerateResult
from renderctl.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    MODEL = "openai/gpt-5.4-image-2"
    PROVIDER_NAME = "openai"

    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult:
        b64 = base64.b64encode(input_file.read_bytes()).decode()
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ],
        }]
        image_data, elapsed_ms = self._post(messages)
        file_path, created_at = self._save(
            image_data, prompt, output_dir,
            {"operation": "edit", "input_file": str(input_file), "generation_time_ms": elapsed_ms},
        )
        return GenerateResult(
            file_path=str(file_path),
            provider=self.PROVIDER_NAME,
            model=self.MODEL,
            generation_time_ms=elapsed_ms,
            created_at=created_at,
        )
