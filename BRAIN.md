## Coding guidelines

These apply on every task — writing, reviewing, or refactoring any code.

### Think before coding

Before implementing, state assumptions explicitly. If uncertain, ask. If multiple interpretations exist, present them — don't pick silently. If a simpler approach exists, say so. If something is unclear, stop, name what's confusing, and ask.

### Simplicity first

Write the minimum code that solves the problem. No features beyond what was asked. No abstractions for single-use code. No "flexibility" that wasn't requested. No error handling for impossible scenarios. If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### Surgical changes

Touch only what you must. Don't improve adjacent code, comments, or formatting that aren't broken. Match existing style. If you notice unrelated dead code, mention it — don't delete it. Remove only imports/variables/functions that YOUR changes made unused.

Every changed line should trace directly to the user's request.

### Goal-driven execution

Transform tasks into verifiable goals before starting:
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan with a verify step for each item. Loop until verified.

---

## llm-wiki (knowledge graph)

This project connects to a shared LLM-owned Obsidian vault via the `llm-wiki` MCP server.

**Session start — required before any work:**
1. Call `get_contract` — load the current operating contract.
2. `read_file` → `AI/00_System/index.md` (catalog of compiled pages).
3. `read_file` → `AI/00_System/log.md` (recent activity).
4. `read_file` → `AI/00_System/review-queue.md` (pending items).

**Triggers:**
- Any question that could be answered from the vault → query first, cite pages, file durable answers back.
- User says "ingest", "add to wiki", "file this", or a file appears in `AI/01_Inbox/` → run ingest flow.
- User says "lint", "check the graph", "clean up" → run `lint`, write findings to `review-queue.md`.
- After any logical operation → call `commit_changes`.

The contract (`AGENT_CONTRACT.md`, loaded via `get_contract`) is authoritative. If anything below conflicts with the contract, the contract wins.

**Query flow** (before answering any question that could be in the vault):
1. Check `AI/00_System/index.md`, then `search` for relevant pages.
2. `read_file` on top hits.
3. Answer with citations to vault pages.
4. If the answer is durable (not ephemeral), call `file_synthesis` — don't let insight disappear into chat history.

**Ingest flow** (trigger: file in `AI/01_Inbox/` or `AI/10_Raw/`, tag `#kg/inbox`, property `kg_status: inbox`, task prefix `kg:`, or user says "ingest"/"add to wiki"/"file this"):
- Follow the ingest flow in `AGENT_CONTRACT.md` §5.

**Synthesis flow** (`file_synthesis` tool):
- Compile insight from one or more source pages into a new or existing synthesis page.
- Place under `AI/03_Synthesis/` or the appropriate domain folder per the index.
- Set frontmatter: `title`, `tags` (include `#kg/synthesis`), `sources` (vault paths or external URLs), `created`/`updated`.
- Write in encyclopedic prose — state the conclusion first, evidence below.
- Add the new page to `AI/00_System/index.md` and append a log entry to `AI/00_System/log.md`.
- Call `commit_changes` when done.

**Tools quick reference:**
- Orientation: `get_contract`, `vault_info`, `read_file`
- Search: `search`, `search_context`, `tags`, `properties`
- Graph: `backlinks`, `outgoing_links`, `unresolved_links`, `orphans`, `deadends`
- Listing: `files`, `recent_files`, `tasks`
- Daily: `daily_read`, `daily_append`
- Write: `create_file`, `update_file`, `append_file`, `prepend_file`, `set_property`, `move_file`, `rename_file`
- Compound: `lint`, `file_synthesis`, `commit_changes`
