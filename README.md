# renderctl

A standalone image generation CLI. Supports OpenAI (`gpt-image-2`) and Google Gemini (`gemini-3.1-flash-image-preview`).

An MCP server adapter (Phase 4) will allow AI agents to invoke the CLI via subprocess.

---

## Install

**Production / MCP deployment** — installs `renderctl` on PATH globally, no venv activation needed:

```bash
uv tool install -e .
```

**Development** — installs into a local venv:

```bash
uv venv
uv pip install -e .
source .venv/bin/activate
```

---

## Configuration

Copy `.env.example` and fill in your keys:

```bash
cp .env.example .env
# edit .env with your keys
```

The CLI loads `.env` automatically on startup — no need to source it.

---

## Commands

### generate

Generate an image from a prompt.

```bash
renderctl generate "a futuristic city at sunset" --output-dir ./outputs
renderctl generate "a futuristic city at sunset" --output-dir ./outputs --provider gemini
renderctl generate --prompt-file ./prompt.txt --output-dir ./outputs
renderctl generate "a cat on mars" --output-dir ./outputs --json
```

### edit

Edit an existing image with a prompt. OpenAI only (Gemini does not support editing).

```bash
renderctl edit input.png "make it cyberpunk" --output-dir ./outputs
renderctl edit input.png --prompt-file ./edit.txt --output-dir ./outputs
renderctl edit input.png "add snow" --output-dir ./outputs --json
```

### list

List all generated images in a directory.

```bash
renderctl list --output-dir ./outputs
renderctl list --output-dir ./outputs --json
```

### inspect

Show metadata for a generated image.

```bash
renderctl inspect ./outputs/20260428_123456_openai_abc12345.png
```

---

## Output

Each `generate` or `edit` run writes two files to `--output-dir`:

- `{timestamp}_{provider}_{hash}.png` — the generated image
- `{timestamp}_{provider}_{hash}.json` — metadata sidecar (prompt, model, timing)

`--json` flag output schema:

```json
{
  "schema_version": "1.0",
  "status": "success",
  "file_path": "...",
  "provider": "openai",
  "model": "gpt-image-2",
  "generation_time_ms": 1234
}
```

---

## Exit codes

| Code | Meaning          |
|------|------------------|
| 0    | success          |
| 1    | general error    |
| 2    | invalid args     |
| 3    | config error     |
| 4    | provider error   |
| 6    | filesystem error |

---

## MCP Server

Coming in Phase 4. The MCP server will be a thin adapter that shells out to `renderctl run <job.json>` and returns the JSON result to the calling agent. No business logic lives in the MCP layer.

---

## Development

```bash
uv venv
uv pip install -e .
source .venv/bin/activate
uv pip install pytest
pytest
```
