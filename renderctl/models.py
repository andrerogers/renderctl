import json
from dataclasses import asdict, dataclass


@dataclass
class GenerateResult:
    schema_version: str = "1.0"
    status: str = "success"
    file_path: str = ""
    provider: str = ""
    model: str = ""
    generation_time_ms: int = 0
    created_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
