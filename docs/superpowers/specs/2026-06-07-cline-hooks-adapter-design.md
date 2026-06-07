# Cline ⇄ agentmemory Hooks Adapter — Design

**Date:** 2026-06-07
**Branch:** `pptx-presentation-generator`
**Status:** Approved (design), pending implementation plan

## Goal

Automate memory **save** and **recall** in the Cline VS Code extension
(`saoudrizwan.claude-dev`) using Cline's native hooks system, so that working in
Cline feeds and draws from agentmemory the same way the existing Claude Code,
Copilot, Codex, and OpenCode adapters already do.

Cline is already wired to agentmemory over MCP (read-only retrieval tools
auto-approved). MCP gives Cline *manual* access to memory tools. This adapter
adds the *automatic* layer: lifecycle hooks that capture activity and inject
recalled context without the model having to call a tool.

## Cline hooks — confirmed contract

Source: Cline docs (`docs.cline.bot/customization/hooks`), the v3.36 release
notes, and the DeepWiki reverse-engineering of the hooks subsystem.

- **Eight hook types:** `TaskStart`, `TaskResume`, `TaskCancel`, `TaskComplete`,
  `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `PreCompact`.
- **I/O:** each hook receives a JSON `HookInput` on **stdin** and returns a JSON
  `HookOutput` on **stdout**.
  - `HookInput` base fields: `clineVersion`, `hookName`, `timestamp`, `taskId`,
    `workspaceRoots` (array of paths), `userId`, plus hook-specific data.
  - `HookOutput`: `cancel` (boolean — blocks the operation when true),
    `contextModification` (string — text injected into the conversation),
    `errorMessage` (string). Deprecated fields like `shouldContinue` are rejected.
- **Discovery:** Cline scans the hooks directory for a file **named exactly the
  hook type**. Missing file ⇒ no-op.
- **Locations:** project `<workspace>/.clinerules/hooks/`, global
  `~/Documents/Cline/Rules/Hooks/`.
- **Platform execution:**
  - **Windows:** hooks run via **PowerShell**; the file is named with a `.ps1`
    extension (e.g. `PreToolUse.ps1`). Enable/disable toggling is not yet
    supported on Windows, but a present hook file always runs.
  - **macOS/Linux:** extensionless file (e.g. `PreToolUse`), must be executable.
- **Timeout:** hooks are terminated after 30,000 ms.

The primary target machine is Windows 10, so the `.ps1` path is the main one; the
repo artifact also ships the extensionless mac/linux variant.

## Approach (settled during brainstorming)

- **Scope:** full parity — recall injection + capture + summarize/consolidate.
- **Implementation:** portable Node scripts (compiled from TS, reusing existing
  auth/project/REST helpers) driven by thin per-platform shims. Not pure
  PowerShell — keeps one code path shared with the other host adapters and stays
  cross-platform.
- **Install:** authored in the repo as the source of truth, plus an installer
  that deploys to the global Cline hooks dir so memory automation applies in
  **every** project opened in Cline.
- **UserPromptSubmit:** observe only by default; recall-injection is env-gated
  (`AGENTMEMORY_INJECT_ON_PROMPT=true`) and off by default to avoid per-turn noise
  (TaskStart already injects context).
- **Blocking:** the adapter **never** sets `cancel:true`. Memory automation is
  purely additive; Cline behaves identically whether or not agentmemory is running.

## Architecture

```
Cline fires hook
   │  (HookInput JSON on stdin)
   ▼
<HookType>.ps1  (Windows shim)   |   <HookType>  (mac/linux node-shebang wrapper)
   │  pipes stdin → node
   ▼
node .agentmemory/<hook>.mjs     (compiled from src/hooks/cline/<hook>.ts)
   │  REST call(s) with Authorization: Bearer <secret>
   ▼
agentmemory REST (/session/start, /observe, /enrich, /summarize,
                  /context, /session/end, /consolidate-pipeline, /crystals/auto)
   │
   ▼  (HookOutput JSON on stdout → Cline injects contextModification)
```

### New source files

- `src/hooks/cline/_cline.ts` — shared helpers:
  - read + JSON-parse stdin into a typed `HookInput`,
  - map `taskId` → `sessionId` and `workspaceRoots[0]` → `cwd`/project
    (reusing `src/hooks/_project.ts` `resolveProject`),
  - `authHeaders()` (Bearer from `AGENTMEMORY_SECRET`), `post()` /
    `postJson()` with `AbortSignal.timeout`,
  - `emit(output)` — always writes a valid `HookOutput` JSON to stdout,
  - config resolution: env first (`AGENTMEMORY_URL`, `AGENTMEMORY_SECRET`),
    then `.agentmemory/config.json` fallback.
- One script per hook:
  `src/hooks/cline/{task-start,task-resume,task-cancel,task-complete,
  pre-tool-use,post-tool-use,prompt-submit,pre-compact}.ts`.

### Hook → behavior mapping

| Cline hook | agentmemory action | Injects context? | Awaits? |
|---|---|---|---|
| `TaskStart` | `POST /session/start {sessionId,project,cwd}` → inject returned `context` + one-time agentmemory instructions block | recall | yes (~1.5s) |
| `TaskResume` | `POST /session/start` (idempotent) + `POST /context` → inject | recall | yes (~1.5s) |
| `UserPromptSubmit` | `POST /observe {hookType:"prompt_submit", data:{prompt, files}}`; recall inject only if `AGENTMEMORY_INJECT_ON_PROMPT=true` | optional | observe fire-and-forget; recall awaits when enabled |
| `PreToolUse` | extract file paths from `parameters` → `POST /enrich {sessionId, files, toolName}` → inject file history/pitfalls | enrich | yes (~1.5s) |
| `PostToolUse` | `POST /observe {hookType: success?"post_tool_use":"post_tool_failure", data:{tool_name, tool_input, tool_output, duration_ms}}` | — | fire-and-forget |
| `PreCompact` | `POST /summarize {sessionId}` + `POST /context` → inject so memory survives compaction | yes | yes (~1.5s) |
| `TaskComplete` | `POST /summarize` + `POST /session/end` + fire-and-forget `/consolidate-pipeline` & `/crystals/auto` | — | summarize/end await; consolidate detached |
| `TaskCancel` | `POST /observe {task_cancel}` + `POST /session/end` (no consolidate) | — | fire-and-forget |

File-path extraction reuses the key set from the OpenCode adapter
(`filePath`, `file_path`, `path`, `file`, `pattern`); Cline tool parameter names
are normalized in `_cline.ts`.

The one-time instructions block (TaskStart) is the same `AGENTMEMORY_INSTRUCTIONS`
text the OpenCode adapter injects, adapted to Cline's `agentmemory_*` MCP tool
names so the model knows the automatic memory tools are available.

## Runtime layout (install target)

Everything needed at run time is self-contained in the Cline hooks dir, so the
hooks do not depend on the repo being present:

```
~/Documents/Cline/Rules/Hooks/
  TaskStart.ps1   TaskResume.ps1   TaskCancel.ps1   TaskComplete.ps1
  PreToolUse.ps1  PostToolUse.ps1  UserPromptSubmit.ps1  PreCompact.ps1   ← Windows shims
  TaskStart  TaskResume  …                                               ← mac/linux wrappers (chmod +x)
  .agentmemory/
    task-start.mjs  …  (8 standalone compiled scripts; helpers inlined per script)
    config.json      (url + bearer secret; gitignored; 0600 on posix)
```

`.agentmemory/` is ignored by Cline's hook scan because its name does not match
any hook type. The `.ps1` shim is minimal:

```powershell
$ErrorActionPreference = 'SilentlyContinue'
$stdin = [Console]::In.ReadToEnd()
$stdin | node "$PSScriptRoot\.agentmemory\task-start.mjs"
```

The mac/linux wrapper is an extensionless node-shebang passthrough (or a direct
copy of the `.mjs` with `#!/usr/bin/env node`), `chmod +x`.

## Repo artifact

```
integrations/cline/
  README.md            ← matches the other integration READMEs (what it does,
                          hook table, install/uninstall, env, troubleshooting)
  install.ps1          ← copies compiled scripts + writes shims + config.json
  install.sh           ← posix equivalent (extensionless wrappers, chmod +x)
  shim.ps1.tmpl        ← shim template (hook name substituted per file)
```

Installer flags:
- default → global dir (`~/Documents/Cline/Rules/Hooks/`),
- `--project <path>` / `-Project` → `<path>/.clinerules/hooks/`,
- `--uninstall` → removes the 8 shims and `.agentmemory/`.

The installer reads the secret from `~/.agentmemory/.env` (or
`$AGENTMEMORY_SECRET`) and the URL from `$AGENTMEMORY_URL`
(default `http://localhost:3111`) to write `config.json`. The secret is never
committed; `config.json` is gitignored at the install location.

Compiled scripts in the repo live at `plugin/cline/scripts/*.mjs` (committed,
matching the existing `plugin/scripts/` convention); the installer copies from
there.

## Build integration

Add the eight `src/hooks/cline/*.ts` entries to `tsdown.config.ts`, each as its
own config block (one entry per block — same reason the existing hooks do this:
prevents tsdown from hoisting shared helpers into hashed chunks across hooks),
output dir `plugin/cline/scripts`. The shared `_cline.ts` and `_project.ts` are
inlined into each script by the bundler, so each `.mjs` is standalone.

## Config & secret handling

1. `AGENTMEMORY_URL` env (default `http://localhost:3111`).
2. `AGENTMEMORY_SECRET` env → `Authorization: Bearer <secret>`.
3. Fallback to `.agentmemory/config.json` next to the compiled scripts when env
   is absent.

Cline-spawned hooks inherit the user environment, and `AGENTMEMORY_SECRET` is
already `setx`-persisted on this machine, so env is the normal path; the config
file is the belt-and-suspenders fallback (e.g. if VS Code was launched before the
env was set).

## Safety / error handling

- **Hooks never block coding.** Every script always emits
  `{cancel:false, contextModification:"<…or empty>", errorMessage:""}` and
  swallows every error. If agentmemory is unreachable (container stopped, wrong
  secret → 401), the hook returns an empty, non-cancelling output and Cline
  proceeds unchanged.
- Injection hooks `await` with a ~1.5s `AbortSignal.timeout`; capture-only hooks
  fire-and-forget with a short register timeout. All well under Cline's 30s limit.
- SDK-child / nested contexts are guarded the same way `session-start.ts` guards
  `isSdkChildContext`, so a Cline-launched sub-agent does not double-register a
  session (if Cline ever exposes that signal; otherwise dedupe on `taskId`).

## Testing

- **Unit (vitest):** for each hook script, feed a representative `HookInput` on a
  mocked stdin, mock `fetch`, and assert (a) the correct REST endpoint + body,
  (b) a valid `HookOutput` is always emitted, (c) `cancel` is always `false`,
  (d) on `fetch` rejection / non-200 the output is still valid and non-cancelling.
- **Mapping tests:** `taskId`→sessionId, `workspaceRoots[0]`→project, file-path
  extraction from sample Cline tool `parameters`.
- **Installer smoke test:** run `install.ps1 --project <tmp>` into a temp dir,
  assert the 8 shims + `.agentmemory/` scripts + `config.json` exist and the
  shim pipes stdin correctly (`echo '{}' | pwsh TaskStart.ps1` returns valid
  JSON). Mirror for `install.sh` on posix.
- **Manual:** install globally, open a project in Cline, run a task, confirm in
  the agentmemory viewer that a session started, observations landed, and a
  summary/consolidation ran on completion.

## Out of scope (YAGNI)

- Policy/lesson-based tool **blocking** (the optional guard hook) — explicitly
  declined; can be added later behind an env flag without touching this design.
- Streaming/SSE — irrelevant; hooks are request/response.
- A Cline *plugin* (SDK `cline.plugins` manifest) — hooks cover the save/recall
  goal; the SDK plugin route is a separate, heavier integration for later.
