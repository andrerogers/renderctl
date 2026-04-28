import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv

load_dotenv()

from renderctl.providers.gemini_provider import GeminiProvider
from renderctl.providers.openai_provider import OpenAIProvider

app = typer.Typer(no_args_is_help=True)

PROVIDERS = {"openai": OpenAIProvider, "gemini": GeminiProvider}


@app.callback()
def main():
    pass


def _resolve_prompt(prompt: Optional[str], prompt_file: Optional[Path]) -> str:
    if prompt and prompt_file:
        typer.echo("Error: provide either a prompt or --prompt-file, not both", err=True)
        raise typer.Exit(2)
    if prompt_file:
        if not prompt_file.exists():
            typer.echo(f"Error: prompt file not found: {prompt_file}", err=True)
            raise typer.Exit(2)
        return prompt_file.read_text().strip()
    if not prompt:
        typer.echo("Error: prompt is required", err=True)
        raise typer.Exit(2)
    return prompt


def _get_provider(provider: str):
    if provider not in PROVIDERS:
        typer.echo(f"Unknown provider: {provider}. Choose from: {', '.join(PROVIDERS)}", err=True)
        raise typer.Exit(2)
    try:
        return PROVIDERS[provider]()
    except ValueError as e:
        typer.echo(f"Config error: {e}", err=True)
        raise typer.Exit(3)


@app.command()
def generate(
    prompt: Annotated[Optional[str], typer.Argument(help="Image prompt")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to write output files")] = ...,
    prompt_file: Annotated[Optional[Path], typer.Option("--prompt-file", help="Path to prompt text file")] = None,
    provider: Annotated[str, typer.Option("--provider", help="Image provider")] = "openai",
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
):
    prompt = _resolve_prompt(prompt, prompt_file)
    p = _get_provider(provider)

    try:
        result = p.generate(prompt, output_dir)
    except Exception as e:
        typer.echo(f"Provider error: {e}", err=True)
        raise typer.Exit(4)

    typer.echo(result.to_json() if json_output else f"Generated: {result.file_path}")


@app.command()
def edit(
    input_file: Annotated[Path, typer.Argument(help="Input image to edit")],
    prompt: Annotated[Optional[str], typer.Argument(help="Edit prompt")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to write output files")] = ...,
    prompt_file: Annotated[Optional[Path], typer.Option("--prompt-file", help="Path to prompt text file")] = None,
    provider: Annotated[str, typer.Option("--provider", help="Image provider")] = "openai",
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
):
    if not input_file.exists():
        typer.echo(f"Error: input file not found: {input_file}", err=True)
        raise typer.Exit(2)

    prompt = _resolve_prompt(prompt, prompt_file)
    p = _get_provider(provider)

    try:
        result = p.edit(input_file, prompt, output_dir)
    except NotImplementedError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)
    except Exception as e:
        typer.echo(f"Provider error: {e}", err=True)
        raise typer.Exit(4)

    typer.echo(result.to_json() if json_output else f"Edited: {result.file_path}")


@app.command("list")
def list_images(
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to list images from")] = ...,
    json_output: Annotated[bool, typer.Option("--json", help="Print result as JSON")] = False,
):
    if not output_dir.exists():
        typer.echo(f"Error: directory not found: {output_dir}", err=True)
        raise typer.Exit(6)

    images = []
    for png in sorted(output_dir.glob("*.png")):
        entry = {"file_path": str(png)}
        sidecar = png.with_suffix(".json")
        if sidecar.exists():
            entry.update(json.loads(sidecar.read_text()))
        images.append(entry)

    if json_output:
        typer.echo(json.dumps(images, indent=2))
    else:
        if not images:
            typer.echo("No images found.")
        for img in images:
            prompt = img.get("prompt", "(no metadata)")
            typer.echo(f"{img['file_path']}  —  {prompt}")


@app.command()
def inspect(
    file: Annotated[Path, typer.Argument(help="Image file to inspect")],
):
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(2)

    sidecar = file.with_suffix(".json")
    if not sidecar.exists():
        typer.echo(f"Error: no metadata found for {file}", err=True)
        raise typer.Exit(1)

    typer.echo(sidecar.read_text())
