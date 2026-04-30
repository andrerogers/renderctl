# renderctl

A standalone image generation CLI. Supports OpenAI GPT Image 2, Google Gemini Nano Banana 2, and Higgsfield (Seedream).

An MCP server adapter allows AI agents to invoke the CLI via subprocess.

---

## Install

**Production / MCP deployment** — installs `renderctl` and `renderctl-mcp` on PATH globally:

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

```bash
cp .env.example .env
# edit .env
```

| Key | Required for |
|-----|-------------|
| `OPENROUTER_API_KEY` | openai, gemini |
| `HIGGSFIELD_API_KEY` | higgsfield |

The CLI loads `.env` automatically on startup.

---

## Commands

### generate

```bash
renderctl generate "a futuristic city at sunset" --output-dir ./outputs
renderctl generate "a futuristic city at sunset" --output-dir ./outputs --provider gemini
renderctl generate "a futuristic city at sunset" --output-dir ./outputs --provider higgsfield
renderctl generate --prompt-file ./prompt.txt --output-dir ./outputs
renderctl generate "a cat on mars" --output-dir ./outputs --json
```

### edit

Edit an existing image. OpenAI only — Gemini and Higgsfield do not support editing.

```bash
renderctl edit input.png "make it cyberpunk" --output-dir ./outputs
renderctl edit input.png --prompt-file ./edit.txt --output-dir ./outputs
renderctl edit input.png "add snow" --output-dir ./outputs --json
```

### run

Execute one or more generation jobs from a JSON file.

```bash
renderctl run job.json
renderctl run batch.json --json
```

**Single job file:**

```json
{
  "operation": "generate",
  "provider": "openai",
  "prompt": "a futuristic city at sunset",
  "output_dir": "./outputs"
}
```

**Batch job file (array):**

```json
[
  {"operation": "generate", "provider": "openai", "prompt": "first image", "output_dir": "./outputs"},
  {"operation": "edit", "provider": "openai", "prompt": "make it cyberpunk", "input_file": "./outputs/foo.png", "output_dir": "./outputs"}
]
```

Supported fields: `operation` (generate/edit), `provider`, `prompt`, `prompt_file`, `output_dir`, `input_file` (edit only). Fails fast on first error. `--json` outputs a JSON array of results.

### list

```bash
renderctl list --output-dir ./outputs
renderctl list --output-dir ./outputs --json
```

### inspect

```bash
renderctl inspect ./outputs/20260428_123456_openai_abc12345.png
```

---

## Providers

| Name | Via | Models | edit |
|------|-----|--------|------|
| `openai` | OpenRouter | `openai/gpt-5.4-image-2` | ✅ |
| `gemini` | OpenRouter | `google/gemini-3.1-flash-image-preview` | ❌ |
| `higgsfield` | Direct API | `bytedance/seedream/v4/text-to-image` | ❌ |

Provider is case-insensitive. No automatic fallback.

---

## Output

Each `generate` or `edit` run writes two files to `--output-dir`:

- `{timestamp}_{provider}_{hash}.png` — the generated image
- `{timestamp}_{provider}_{hash}.json` — metadata sidecar (prompt, model, timing)

`--json` output schema:

```json
{
  "schema_version": "1.0",
  "status": "success",
  "file_path": "...",
  "provider": "openai",
  "model": "openai/gpt-5.4-image-2",
  "generation_time_ms": 1234,
  "created_at": "..."
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
| 5    | safety refusal   |
| 6    | filesystem error |

---

## MCP Server

Registered as a Claude Code tool:

```bash
claude mcp add renderctl -- renderctl-mcp
```

Tools: `generate_image`, `edit_image`, `list_images`. All shell out to `renderctl ... --json` and validate `schema_version == "1.0"` before returning.

---

## Development

```bash
uv venv && uv pip install -e . && source .venv/bin/activate
uv pip install pytest
pytest
```
