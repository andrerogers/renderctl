# renderctl Playbook

Manual test guide for all CLI commands and the MCP server.

---

## Prerequisites

```bash
# Dev install — local venv, requires activation each session
uv venv
uv pip install -e .
source .venv/bin/activate

# Production / MCP install — renderctl on PATH globally, no activation needed
uv tool install -e .

# API keys — copy and fill in .env
cp .env.example .env
# edit .env:
#   OPENROUTER_API_KEY=sk-or-...
#   HIGGSFIELD_API_KEY=...

# Working directory for outputs
mkdir -p /tmp/renderctl-test
```

Verify the install:

```bash
renderctl --help
```

Expected: lists `generate`, `edit`, `run`, `list`, `inspect` commands.

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

**Check:** JSON with `schema_version`, `status`, `file_path`, `provider`, `model`, `generation_time_ms`, `created_at`.

---

## 3. generate — prompt file

```bash
echo "a neon-lit Tokyo street at midnight" > /tmp/prompt.txt

renderctl generate \
  --prompt-file /tmp/prompt.txt \
  --output-dir /tmp/renderctl-test \
  --provider openai
```

**Check:** Sidecar prompt matches file contents.

---

## 4. generate — Gemini

```bash
renderctl generate "a red panda in a bamboo forest" \
  --output-dir /tmp/renderctl-test \
  --provider gemini
```

**Check:** Filename contains `_gemini_`. Sidecar `"provider": "gemini"`, `"model": "google/gemini-3.1-flash-image-preview"`.

---

## 5. generate — Higgsfield

```bash
renderctl generate "a red panda in a bamboo forest" \
  --output-dir /tmp/renderctl-test \
  --provider higgsfield
```

**Check:**

- Filename contains `_higgsfield_`
- Sidecar `"provider": "higgsfield"`, `"model": "bytedance/seedream/v4/text-to-image"`
- Generation takes longer than OpenAI/Gemini (async poll)

---

## 6. edit — OpenAI

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

renderctl edit "$INPUT" "make it cyberpunk with neon lights" \
  --output-dir /tmp/renderctl-test \
  --provider openai
```

**Check:** New PNG + sidecar with `"operation": "edit"` and `"input_file"` pointing to source.

---

## 7. edit — Gemini (should fail gracefully)

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

renderctl edit "$INPUT" "make it cyberpunk" \
  --output-dir /tmp/renderctl-test \
  --provider gemini
echo "Exit: $?"
```

**Check:** Exits 2. Error: `edit is not supported by the gemini provider`.

---

## 8. edit — Higgsfield (should fail gracefully)

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

renderctl edit "$INPUT" "make it cyberpunk" \
  --output-dir /tmp/renderctl-test \
  --provider higgsfield
echo "Exit: $?"
```

**Check:** Exits 2. Error: `edit is not supported by the higgsfield provider`.

---

## 9. run — single job

```bash
cat > /tmp/job.json <<'EOF'
{
  "operation": "generate",
  "provider": "openai",
  "prompt": "a serene mountain lake at dawn",
  "output_dir": "/tmp/renderctl-test"
}
EOF

renderctl run /tmp/job.json
```

**Check:** One new PNG + sidecar written.

---

## 10. run — batch jobs

```bash
cat > /tmp/batch.json <<'EOF'
[
  {
    "operation": "generate",
    "provider": "openai",
    "prompt": "a cyberpunk city",
    "output_dir": "/tmp/renderctl-test"
  },
  {
    "operation": "generate",
    "provider": "gemini",
    "prompt": "a watercolor forest",
    "output_dir": "/tmp/renderctl-test"
  }
]
EOF

renderctl run /tmp/batch.json
```

**Check:** Two new PNGs written, one per provider.

---

## 11. run — JSON output

```bash
renderctl run /tmp/batch.json --json
```

**Check:** JSON array with two objects, each having `schema_version`, `status`, `provider`, `file_path`.

---

## 12. run — edit job

```bash
INPUT=$(ls /tmp/renderctl-test/*.png | head -1)

cat > /tmp/edit-job.json <<EOF
{
  "operation": "edit",
  "provider": "openai",
  "prompt": "add falling snow",
  "input_file": "$INPUT",
  "output_dir": "/tmp/renderctl-test"
}
EOF

renderctl run /tmp/edit-job.json
```

**Check:** New PNG + sidecar with `"operation": "edit"`.

---

## 13. list

```bash
renderctl list --output-dir /tmp/renderctl-test
renderctl list --output-dir /tmp/renderctl-test --json
```

**Check:** One line / one JSON entry per PNG.

---

## 14. inspect

```bash
FILE=$(ls /tmp/renderctl-test/*.png | head -1)
renderctl inspect "$FILE"
```

**Check:** Prints sidecar JSON.

---

## 15. inspect — missing sidecar (exit 1)

```bash
touch /tmp/renderctl-test/orphan.png
renderctl inspect /tmp/renderctl-test/orphan.png
echo "Exit: $?"
```

**Check:** Exit 1.

---

## 16. Error cases

| Command | Expected exit |
|---------|--------------|
| `renderctl generate --output-dir /tmp/renderctl-test` | 2 (no prompt) |
| `renderctl generate "x" --output-dir /tmp/renderctl-test` with `OPENROUTER_API_KEY` unset | 3 (config error) |
| `renderctl generate "x" --provider badprovider --output-dir /tmp/renderctl-test` | 2 (unknown provider) |
| `renderctl list --output-dir /tmp/does-not-exist` | 6 (filesystem error) |
| `renderctl inspect /tmp/does-not-exist.png` | 6 (file not found) |
| `renderctl run /tmp/nonexistent.json` | 2 (job file not found) |
| `renderctl generate "x" --provider higgsfield --output-dir /tmp/renderctl-test` with `HIGGSFIELD_API_KEY` unset | 3 (config error) |

---

## MCP Server

Entry point: `renderctl-mcp` (stdio transport, FastMCP). Tools: `generate_image`, `edit_image`, `list_images`.

### Prerequisites

```bash
uv tool install -e .
claude mcp add renderctl -- renderctl-mcp

# Verify inside a Claude Code session
/mcp
# Expected: renderctl listed with generate_image, edit_image, list_images
```

---

### 17. generate_image

> "Generate an image of a red panda in a bamboo forest using OpenAI and save it to /tmp/renderctl-test"

**Check:** Claude calls `generate_image`. Returns JSON with `schema_version: "1.0"`, `status: "success"`, `file_path`. File exists on disk.

---

### 18. edit_image

> "Edit /tmp/renderctl-test/<file>.png — add snow"

**Check:** Claude calls `edit_image`. New PNG + sidecar with `"operation": "edit"` and `"input_file"`.

---

### 19. list_images

> "List all images in /tmp/renderctl-test"

**Check:** Claude calls `list_images`. Returns array of objects with `file_path` + sidecar fields.

---

### 20. MCP error propagation

Ask Claude to generate without `OPENROUTER_API_KEY` set.

**Check:** MCP surfaces `OPENROUTER_API_KEY not set`. No crash or silent failure.

---

### 21. Version lock check

After any CLI change that bumps `schema_version`:

```bash
python -c "
from renderctl.mcp_server import _run
# Test _run with a patched schema_version response — should raise RuntimeError: schema version mismatch
"
```
