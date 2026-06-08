# agentmemory ⇄ Cline hooks

Automatic memory **save** and **recall** for the Cline VS Code extension via
Cline's native hooks. Complements the MCP wiring (which gives Cline manual
memory tools) by capturing activity and injecting recalled context
automatically — no tool call required.

## What each hook does

| Cline hook | Action |
|---|---|
| `TaskStart` | Registers the session, injects recalled context + memory instructions |
| `TaskResume` | Re-injects session context after an interruption |
| `PreToolUse` | Injects a file's past pitfalls/history before an edit (never blocks) |
| `PostToolUse` | Captures tool outcome (success or failure) |
| `UserPromptSubmit` | Records the prompt; optional recall injection (env-gated) |
| `PreCompact` | Summarizes + injects context so memory survives compaction |
| `TaskComplete` | Summarizes, ends the session, runs consolidation |
| `TaskCancel` | Ends the session on cancellation |

The adapter **never cancels** an operation — Cline behaves identically whether
or not agentmemory is running.

## Install

Build first so the compiled scripts exist:

    npx tsdown

Global (applies in every project you open in Cline):

    # Windows (PowerShell)
    ./integrations/cline/install.ps1
    # macOS/Linux
    ./integrations/cline/install.sh

Project-only (this repo / a specific workspace):

    ./integrations/cline/install.ps1 -Project F:\some\repo
    ./integrations/cline/install.sh --project=/some/repo

Uninstall: add `-Uninstall` (PowerShell) or `--uninstall` (sh).

Restart VS Code (the extension host re-reads env and re-scans hooks on restart).

## Authentication

The hooks POST to agentmemory's REST API, which is guarded by the same
`AGENTMEMORY_SECRET` as the MCP endpoint. Resolution order:

1. `AGENTMEMORY_SECRET` / `AGENTMEMORY_URL` environment variables (inherited by
   Cline-spawned hook processes).
2. `<hooks-dir>/.agentmemory/config.json`, written by the installer from
   `~/.agentmemory/.env`. This file holds the bearer secret — it is gitignored
   and written `0600` on POSIX.

If no secret is set anywhere, the hooks send no `Authorization` header (correct
for an open local deployment). If a secret IS required but missing, the server
returns 401 and the hooks silently no-op.

## Optional: recall on every prompt

Off by default. Set `AGENTMEMORY_INJECT_ON_PROMPT=true` to run a `smart-search`
on each prompt and inject the top matches. `TaskStart` already injects context,
so leave this off unless you want per-turn recall.

## Platform notes

Windows runs hooks via PowerShell (`<Hook>.ps1`); macOS/Linux uses executable
extensionless wrappers. Both shim into the same compiled Node scripts under
`.agentmemory/`. 30s hook timeout (we stay well under it).
