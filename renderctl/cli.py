import json
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated, NoReturn, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from renderctl import __version__
from renderctl.providers.base import SafetyRefusalError
from renderctl.providers.gemini_provider import GeminiProvider
from renderctl.providers.higgsfield_provider import HiggsFieldProvider
from renderctl.providers.openai_provider import OpenAIProvider

app = typer.Typer(no_args_is_help=True)
console = Console(stderr=True)

PROVIDERS = {"openai": OpenAIProvider, "gemini": GeminiProvider, "higgsfield": HiggsFieldProvider}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"renderctl {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit"),
    ] = None,
) -> None:
    pass


def _emit_error(msg: str, exit_code: int, json_output: bool = False) -> NoReturn:
    if json_output:
        typer.echo(json.dumps({"schema_version": "1.0", "status": "error", "error_message": msg}))
    else:
        typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(exit_code)


def _resolve_prompt(prompt: Optional[str], prompt_file: Optional[Path], json_output: bool = False) -> str:
    if prompt and prompt_file:
        _emit_error("provide either a prompt or --prompt-file, not both", 2, json_output)
    if prompt_file:
        if not prompt_file.exists():
            _emit_error(f"prompt file not found: {prompt_file}", 2, json_output)
        text = prompt_file.read_text(encoding="utf-8").rstrip()
        if not text:
            _emit_error("prompt file is empty", 2, json_output)
        return text
    if not prompt:
        _emit_error("prompt is required", 2, json_output)
    return prompt  # type: ignore[return-value]


def _get_provider(provider: str, json_output: bool = False):
    provider = provider.lower()
    if provider not in PROVIDERS:
        _emit_error(f"unknown provider: {provider}. choose from: {', '.join(PROVIDERS)}", 2, json_output)
    try:
        return PROVIDERS[provider]()
    except ValueError as e:
        _emit_error(str(e), 3, json_output)


@app.command()
def generate(
    prompt: Annotated[Optional[str], typer.Argument(help="Image prompt")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to write output files")] = ...,
    prompt_file: Annotated[Optional[Path], typer.Option("--prompt-file", help="Path to prompt text file")] = None,
    provider: Annotated[str, typer.Option("--provider", help="Image provider")] = "openai",
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
) -> None:
    """Generate an image from a prompt."""
    prompt = _resolve_prompt(prompt, prompt_file, json_output)
    p = _get_provider(provider, json_output)

    try:
        with console.status("Generating…") if not json_output else nullcontext():
            result = p.generate(prompt, output_dir)
    except SafetyRefusalError as e:
        _emit_error(str(e), 5, json_output)
    except Exception as e:
        _emit_error(str(e), 4, json_output)

    typer.echo(result.to_json() if json_output else f"Generated: {result.file_path}")


@app.command()
def edit(
    input_file: Annotated[Path, typer.Argument(help="Input image to edit")],
    prompt: Annotated[Optional[str], typer.Argument(help="Edit prompt")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to write output files")] = ...,
    prompt_file: Annotated[Optional[Path], typer.Option("--prompt-file", help="Path to prompt text file")] = None,
    provider: Annotated[str, typer.Option("--provider", help="Image provider")] = "openai",
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
) -> None:
    """Edit an existing image with a prompt (OpenAI only)."""
    if not input_file.exists():
        _emit_error(f"input file not found: {input_file}", 2, json_output)

    prompt = _resolve_prompt(prompt, prompt_file, json_output)
    p = _get_provider(provider, json_output)

    try:
        with console.status("Editing…") if not json_output else nullcontext():
            result = p.edit(input_file, prompt, output_dir)
    except NotImplementedError as e:
        _emit_error(str(e), 2, json_output)
    except SafetyRefusalError as e:
        _emit_error(str(e), 5, json_output)
    except Exception as e:
        _emit_error(str(e), 4, json_output)

    typer.echo(result.to_json() if json_output else f"Edited: {result.file_path}")


@app.command("list")
def list_images(
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to list images from")] = ...,
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
) -> None:
    """List all generated images in a directory."""
    if not output_dir.exists():
        _emit_error(f"directory not found: {output_dir}", 6, json_output)

    images = []
    for png in sorted(output_dir.glob("*.png")):
        entry: dict = {"file_path": str(png)}
        sidecar = png.with_suffix(".json")
        if sidecar.exists():
            try:
                entry.update(json.loads(sidecar.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                entry["metadata_error"] = "corrupt sidecar"
        images.append(entry)

    if json_output:
        typer.echo(json.dumps(images, indent=2))
    else:
        if not images:
            typer.echo("No images found.")
        for img in images:
            prompt_text = img.get("prompt", "(no metadata)")
            typer.echo(f"{img['file_path']}  —  {prompt_text}")


@app.command()
def inspect(
    file: Annotated[Path, typer.Argument(help="Image file to inspect")],
) -> None:
    """Show metadata sidecar for a generated image."""
    if not file.exists():
        _emit_error(f"file not found: {file}", 6)

    sidecar = file.with_suffix(".json")
    if not sidecar.exists():
        _emit_error(f"no metadata found for {file}", 1)

    typer.echo(json.dumps(json.loads(sidecar.read_text(encoding="utf-8")), indent=2))


@app.command()
def run(
    job_file: Annotated[Path, typer.Argument(help="Path to JSON job file (single job or array of jobs)")],
    json_output: Annotated[bool, typer.Option("--json", help="Print results as JSON")] = False,
) -> None:
    """Execute one or more generation jobs from a JSON file."""
    if not job_file.exists():
        _emit_error(f"job file not found: {job_file}", 2, json_output)

    try:
        raw = json.loads(job_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _emit_error(f"invalid JSON in job file: {e}", 2, json_output)

    jobs = raw if isinstance(raw, list) else [raw]
    results = []

    for i, job in enumerate(jobs):
        operation = job.get("operation")
        if operation not in ("generate", "edit"):
            _emit_error(f"job {i}: unsupported operation: {operation!r}", 2, json_output)

        if "output_dir" not in job:
            _emit_error(f"job {i}: output_dir is required", 2, json_output)
        output_dir = Path(job["output_dir"])

        prompt_text = job.get("prompt")
        prompt_file_path = job.get("prompt_file")
        if prompt_text and prompt_file_path:
            _emit_error(f"job {i}: provide either prompt or prompt_file, not both", 2, json_output)
        if prompt_file_path:
            pf = Path(prompt_file_path)
            if not pf.exists():
                _emit_error(f"job {i}: prompt file not found: {pf}", 2, json_output)
            prompt_text = pf.read_text(encoding="utf-8").rstrip()
            if not prompt_text:
                _emit_error(f"job {i}: prompt file is empty", 2, json_output)
        if not prompt_text:
            _emit_error(f"job {i}: prompt is required", 2, json_output)

        p = _get_provider(job.get("provider", "openai"), json_output)

        try:
            label = f"Job {i + 1}/{len(jobs)}…"
            with console.status(label) if not json_output else nullcontext():
                if operation == "generate":
                    result = p.generate(prompt_text, output_dir)
                else:
                    input_file_str = job.get("input_file")
                    if not input_file_str:
                        _emit_error(f"job {i}: input_file is required for edit", 2, json_output)
                    input_file = Path(input_file_str)
                    if not input_file.exists():
                        _emit_error(f"job {i}: input_file not found: {input_file}", 2, json_output)
                    result = p.edit(input_file, prompt_text, output_dir)
        except NotImplementedError as e:
            _emit_error(str(e), 2, json_output)
        except SafetyRefusalError as e:
            _emit_error(str(e), 5, json_output)
        except Exception as e:
            _emit_error(str(e), 4, json_output)

        results.append(json.loads(result.to_json()))
        if not json_output:
            action = "Generated" if operation == "generate" else "Edited"
            typer.echo(f"{action}: {result.file_path}")

    if json_output:
        typer.echo(json.dumps(results, indent=2))
