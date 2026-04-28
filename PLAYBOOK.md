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

# API keys — copy and fill in .env (the CLI loads it automatically)
cp .env.example .env
# edit .env with your keys

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
- Sidecar contains correct prompt and `"provider": "openai"`

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
- Sidecar `"provider": "gemini"`, `"model": "gemini-3.1-flash-image-preview"`

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
| `renderctl generate "x" --output-dir /tmp/renderctl-test` with `OPENAI_API_KEY` unset | 3 (config error)     |
| `renderctl generate "x" --provider badprovider --output-dir /tmp/renderctl-test`      | 2 (unknown provider) |
| `renderctl list --output-dir /tmp/does-not-exist`                                     | 6 (filesystem error) |
| `renderctl inspect /tmp/does-not-exist.png`                                           | 2 (file not found)   |

---

## MCP Server (Phase 4 — not yet implemented)

> Complete this section after Phase 4 is shipped.

### Prerequisites

```bash
# Install as a uv tool (puts renderctl on PATH — no venv activation needed by the harness)
uv tool install -e ".[mcp]"

# Start the MCP server
renderctl-mcp
```

### Tool: generate_image

Send a `generate_image` tool call:

```json
{
  "tool": "generate_image",
  "input": {
    "prompt": "a red panda in a bamboo forest",
    "provider": "openai",
    "output_dir": "/tmp/renderctl-test"
  }
}
```

**Check:**

- MCP returns JSON matching the `GenerateResult` schema
- `schema_version` matches the CLI version
- File exists on disk at `file_path`

### Tool: edit_image

```json
{
  "tool": "edit_image",
  "input": {
    "input_file": "/tmp/renderctl-test/<file>.png",
    "prompt": "add snow",
    "provider": "openai",
    "output_dir": "/tmp/renderctl-test"
  }
}
```

### Tool: list_generated_images

```json
{
  "tool": "list_generated_images",
  "input": {
    "output_dir": "/tmp/renderctl-test"
  }
}
```

**Check:** Returns same structure as `renderctl list --json`.

### Version lock check

After any CLI update, confirm the MCP server rejects mismatched `schema_version` and surfaces a clear error to the agent.
