from pathlib import Path

from renderctl.models import GenerateResult
from renderctl.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    MODEL = "google/gemini-3.1-flash-image-preview"
    PROVIDER_NAME = "gemini"

    def edit(self, input_file: Path, prompt: str, output_dir: Path) -> GenerateResult:
        raise NotImplementedError("edit is not supported by the gemini provider")
