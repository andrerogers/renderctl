# PROJECT: Renderctl CLI + MCP Bridge

## Overview

This project defines a **standalone image generation CLI (`renderctl`)** that can also be **invoked by an MCP server** as part of an AI harness.

The architectural model:

* The **CLI is the primary system**
* The **MCP server is a thin adapter** that invokes the CLI via subprocess

Supported providers:

1. **OpenAI GPT Image 2 (`openai/gpt-5.4-image-2` via OpenRouter)**
2. **Google Gemini Nano Banana 2 (`google/gemini-3.1-flash-image-preview` via OpenRouter)**
3. **Higgsfield Seedream (`bytedance/seedream/v4/text-to-image` via direct API)**

---

## Core Design Principle

> **The CLI is the source of truth. MCP is just an adapter.**

All logic lives in the CLI:

* generation
* editing
* validation
* output handling
* retries
* provider abstraction

The MCP server:

* does NOT implement business logic
* does NOT call providers directly
* ONLY shells out to the CLI

### Version Locking

CLI and MCP are **strictly version locked**.

Requirements:

* MCP depends on a specific CLI version
* CLI JSON output includes a schema version
* MCP validates schema version before returning results
* Breaking CLI changes require MCP updates in the same release
* CI includes MCP → CLI integration tests

---

## Architecture

```text
           ┌──────────────────────┐
           │      AI Agent        │
           └─────────┬────────────┘
                     │ MCP
           ┌─────────▼────────────┐
           │   MCP Server (thin)  │
           └─────────┬────────────┘
                     │ subprocess
           ┌─────────▼────────────┐
           │     renderctl CLI    │
           └─────────┬────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
┌───────▼────────┐      ┌──────────▼─────────┐
│ OpenAI Provider │      │ Gemini Provider   │
└────────────────┘      └────────────────────┘
```

---

## CLI Design

### Name

```bash
renderctl
```

---

## Input Model

File-based input is **first-class**.

### Supported modes

#### Direct prompt

```bash
renderctl generate "a futuristic city at sunset" --provider openai
```

#### Prompt file

```bash
renderctl generate --prompt-file ./prompt.txt --provider openai
```

#### Structured job file (preferred for MCP)

```bash
renderctl run ./job.json
```

---

## Job File Format (v1)

JSON only.

```json
{
  "operation": "generate",
  "provider": "openai",
  "prompt": "a futuristic city at sunset",
  "output_dir": "./outputs",
  "format": "png"
}
```

### Supported operations (v1)

* `generate`
* `edit`

---

## CLI Commands

### Generate

```bash
renderctl generate "prompt"
renderctl generate --prompt-file ./prompt.txt
```

### Edit

```bash
renderctl edit input.png "make it cyberpunk"
renderctl edit input.png --prompt-file ./edit.txt
```

### Run (MCP entrypoint)

```bash
renderctl run job.json
```

### List

```bash
renderctl list
```

### Inspect

```bash
renderctl inspect <file>
```

### Doctor

```bash
renderctl doctor
```

---

## CLI Responsibilities

The CLI owns:

* provider selection
* file parsing (prompt + job files)
* API calls
* validation
* retries
* file output
* metadata
* JSON output formatting

---

## MCP Server Design

### Role

Thin wrapper over CLI.

### Execution Flow

1. Receive tool call
2. Write temp job file
3. Execute:

   ```bash
   renderctl run <job-file> --json
   ```
4. Parse JSON output
5. Return result
6. Delete job file (unless debug mode)

### Tool Mapping

| MCP Tool              | CLI                    |
| --------------------- | ---------------------- |
| generate_image        | renderctl run job.json |
| edit_image            | renderctl run job.json |
| list_generated_images | renderctl list --json  |

---

## Provider Strategy

### Explicit selection only

No automatic fallback.

Allowed:

```bash
renderctl generate --provider openai
renderctl generate --provider gemini
```

Optional future:

```bash
--fallback-provider gemini
```

---

## Output Model

### Directory

```
~/.brainstack/generated-images/
```

### Filename

```
{timestamp}_{provider}_{hash}.png
```

### JSON Output

```json
{
  "schema_version": "1.0",
  "status": "success",
  "file_path": "...",
  "provider": "openai",
  "model": "openai/gpt-5.4-image-2",
  "generation_time_ms": 1234
}
```

### Metadata Sidecar

```json
{
  "prompt": "...",
  "provider": "openai",
  "model": "openai/gpt-5.4-image-2",
  "created_at": "...",
  "generation_time_ms": 1234
}
```

---

## Error Handling

### CLI

* JSON errors (`--json`)
* human-readable otherwise
* non-zero exit codes

### MCP

* no custom logic
* surfaces CLI errors directly
* validates schema version

---

## Exit Codes

| Code | Meaning                      |
| ---- | ---------------------------- |
| 0    | success                      |
| 1    | general error                |
| 2    | invalid args                 |
| 3    | config error                 |
| 4    | provider error               |
| 5    | safety refusal (implemented) |
| 6    | filesystem error             |

---

## Configuration

### Environment

* `OPENROUTER_API_KEY` — required for openai, gemini; set in `.env` or shell environment
* `HIGGSFIELD_API_KEY` — required for higgsfield; set in `.env` or shell environment

### Future configuration (not yet implemented)

* `IMAGE_OUTPUT_DIR` env var — default output directory
* `~/.config/renderctl/config.toml` — persistent config file

---

## Temp File Handling (MCP)

* Default: delete job files
* Debug mode: retain files
* Debug logs include file path

---

## Repo Structure

```
renderctl/
  cli/
  providers/
  commands/
  models/
  mcp_server/
  tests/
  fixtures/
```

---

## Delivery Phases

### Phase 1

* CLI skeleton
* OpenAI generate

### Phase 2

* Gemini support

### Phase 3

* edit / list / inspect
* metadata sidecars

### Phase 4

* MCP bridge
* version locking
* integration tests

### Phase 5 (partial — complete)

* retries — 3 attempts, exponential backoff on 429/5xx in `BaseProvider._post`
* batch jobs — `renderctl run <job.json>` accepts single job dict or array
* Higgsfield provider — async poll, direct API, `HIGGSFIELD_API_KEY`

### Phase 5 (deferred)

* explicit fallback (`--fallback-provider`)
* daemon mode (optional)

---

## Key Decision

This project **inverts the original MCP design**:

* CLI = core system
* MCP = integration layer

Result:

* reusable
* testable
* portable
* agent-independent

---

## Final Decisions

* CLI + MCP in same repo
* Version locked
* JSON job files only
* Raw text prompt files
* `run` supports only generate/edit
* Explicit provider selection
* No streaming logs
* Temp files deleted unless debug

---

## Remaining Questions

1. Should the tool be public or internal-only?
2. Ship OpenAI + Gemini together, or stage rollout?
3. Should MCP control output directory per run?
4. Should we publish a formal JSON Schema for `run`?

