# renderctl Playbook

Manual test guide for the CLI (Phases 1–3) and MCP server (Phase 4, when available).

---

## Prerequisites

```bash
# Dev install — local venv, requires activation each session
uv venv
uv pip install -e .
source .venv/bin/activate

# Production / MCP install — renderctl on PATH globally, no activation needed
uv tool install -e .

# API key — copy and fill in .env (the CLI loads it automatically)
cp .env.example .env
# edit .env — set OPENROUTER_API_KEY=sk-or-...

# Working directory for outputs
mkdir -p /tmp/renderctl-test
```

Verify the install:

```bash
renderctl --help
```

Expected: lists `generate`, `edit`, `list`, `inspect` commands.

---

## 1. generate — OpenAI

```bash
renderctl generate "a red panda in a bamboo forest" \
  --output-dir /tmp/renderctl-test \
  --provider openai
```

**Check:**

- Prints `Generated: /tmp/renderctl-test/<timestamp>_openai_<hash>.png`
- Two files exist: `.png` + `.json`
- Sidecar contains correct prompt, `"provider": "openai"`, `"model": "openai/gpt-5.4-image-2"`

```bash
cat /tmp/renderctl-test/*.json
```

---

## 2. generate — JSON output

```bash
renderctl generate "a red panda in a bamboo forest" \
  --output-dir /tmp/renderctl-test \
  --provider openai \
  --json
```

**Check:**

- Output is valid JSON with `schema_version`, `status`, `file_path`, `provider`, `model`, `generation_time_ms`

---

## 3. generate — prompt file

```bash
echo "a neon-lit Tokyo street at midnight" > /tmp/prompt.txt

renderctl generate \
  --prompt-file /tmp/prompt.txt \
  --output-dir /tmp/renderctl-test \
  --provider openai
```

**Check:** Same as test 1. Sidecar prompt matches the file contents.

---

## 4. generate — Gemini

```bash
renderctl generate "a red panda in a bamboo forest" \
  --output-dir /tmp/renderctl-test \
  --provider gemini
```

**Check:**

- Filename contains `_gemini_`
- Sidecar `"provider": "gemini"`, `"model": "google/gemini-3.1-flash-image-preview"`

---

## 5. edit — OpenAI

Requires an existing PNG. Use one produced by a previous generate run.

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

renderctl edit "$INPUT" "make it cyberpunk with neon lights" \
  --output-dir /tmp/renderctl-test \
  --provider openai
```

**Check:**

- New PNG + sidecar written
- Sidecar contains `"operation": "edit"` and `"input_file"` pointing to the source image

---

## 6. edit — Gemini (should fail gracefully)

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

renderctl edit "$INPUT" "make it cyberpunk" \
  --output-dir /tmp/renderctl-test \
  --provider gemini
```

**Check:**

- Exits with code 2
- Error message: `Error: edit is not supported by the gemini provider`

```bash
echo "Exit: $?"
```

---

## 7. list

```bash
renderctl list --output-dir /tmp/renderctl-test
```

**Check:** One line per PNG showing file path and prompt.

```bash
renderctl list --output-dir /tmp/renderctl-test --json
```

**Check:** JSON array; each entry has `file_path` + sidecar fields.

---

## 8. inspect

```bash
FILE=$(ls /tmp/renderctl-test/*.png | head -1)
renderctl inspect "$FILE"
```

**Check:** Prints the sidecar JSON for that image.

---

## 9. inspect — missing sidecar (exit 1)

```bash
touch /tmp/renderctl-test/orphan.png
renderctl inspect /tmp/renderctl-test/orphan.png
echo "Exit: $?"
```

**Check:** Exit code 1, error message about missing metadata.

---

## 10. Error cases

| Command                                                                               | Expected exit        |
| ------------------------------------------------------------------------------------- | -------------------- |
| `renderctl generate --output-dir /tmp/renderctl-test`                                 | 2 (no prompt)        |
| `renderctl generate "x" --output-dir /tmp/renderctl-test` with `OPENROUTER_API_KEY` unset | 3 (config error)     |
| `renderctl generate "x" --provider badprovider --output-dir /tmp/renderctl-test`      | 2 (unknown provider) |
| `renderctl list --output-dir /tmp/does-not-exist`                                     | 6 (filesystem error) |
| `renderctl inspect /tmp/does-not-exist.png`                                           | 2 (file not found)   |

---

## MCP Server (Phase 4)

Entry point: `renderctl-mcp` (stdio transport, FastMCP). Tools: `generate_image`, `edit_image`, `list_images`.

### Prerequisites

```bash
# Install as a uv tool — puts both renderctl and renderctl-mcp on PATH
uv tool install -e .

# Register with Claude Code
claude mcp add renderctl -- renderctl-mcp

# Verify — run inside a Claude Code session
/mcp
# Expected: renderctl listed with generate_image, edit_image, list_images
```

---

### 11. generate_image

Ask Claude Code (with renderctl MCP active):

> "Generate an image of a red panda in a bamboo forest using OpenAI and save it to /tmp/renderctl-test"

**Check:**

- Claude calls `generate_image` tool
- Returns JSON with `schema_version: "1.0"`, `status: "success"`, `file_path`, `provider`, `created_at`
- File exists on disk at `file_path`
- Sidecar `.json` written alongside the PNG

---

### 12. edit_image

> "Edit /tmp/renderctl-test/<file>.png — add snow"

**Check:**

- Claude calls `edit_image` tool
- New PNG + sidecar written to output dir
- Sidecar contains `"operation": "edit"` and `"input_file"`

---

### 13. list_images

> "List all images in /tmp/renderctl-test"

**Check:**

- Claude calls `list_images` tool
- Returns array of objects, each with `file_path` and sidecar fields

---

### 14. MCP error propagation

Ask Claude to generate an image without setting `OPENROUTER_API_KEY`:

**Check:**

- MCP surfaces the error message from the CLI (`OPENROUTER_API_KEY not set`)
- No crash or silent failure

---

### 15. Version lock check

After any CLI change that bumps `schema_version`:

```bash
# Confirm MCP server rejects the mismatch
python -c "
from renderctl.mcp_server import _run
import json
# Manually test _run with a patched schema_version response
"
```

The `_run()` helper raises `RuntimeError: schema version mismatch` and the MCP tool surfaces it to the agent.
