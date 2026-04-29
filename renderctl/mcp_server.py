import json
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

SCHEMA_VERSION = "1.0"

mcp = FastMCP("renderctl")


def _run(args: list[str]) -> dict | list:
    result = subprocess.run(
        [sys.executable, "-m", "renderctl", *args, "--json"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(result.stderr.strip() or f"renderctl exited {result.returncode} with no output")

    if isinstance(data, dict):
        if data.get("status") == "error":
            raise RuntimeError(data.get("error_message", "unknown error"))
        if data.get("schema_version") and data["schema_version"] != SCHEMA_VERSION:
            raise RuntimeError(
                f"schema version mismatch: expected {SCHEMA_VERSION}, got {data['schema_version']}"
            )

    return data


@mcp.tool()
def generate_image(prompt: str, output_dir: str, provider: str = "openai") -> dict:
    """Generate an image from a text prompt."""
    return _run(["generate", prompt, "--output-dir", output_dir, "--provider", provider])


@mcp.tool()
def edit_image(input_file: str, prompt: str, output_dir: str, provider: str = "openai") -> dict:
    """Edit an existing image with a text prompt. OpenAI only; Gemini not supported."""
    return _run(["edit", input_file, prompt, "--output-dir", output_dir, "--provider", provider])


@mcp.tool()
def list_images(output_dir: str) -> list:
    """List all generated images in a directory with their metadata."""
    return _run(["list", "--output-dir", output_dir])


def main() -> None:
    mcp.run(transport="stdio")
