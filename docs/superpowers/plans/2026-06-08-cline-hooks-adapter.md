# Cline Hooks Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Cline VS Code hooks adapter that automatically saves activity to and recalls context from agentmemory, authenticated with the same `AGENTMEMORY_SECRET` the deployment already uses.

**Architecture:** Eight thin hook scripts (compiled from TS) are driven by per-platform shims that Cline discovers in its hooks directory. All logic lives in a shared, dependency-injected `_cline.ts` module so it is unit-testable without spawning processes. Scripts POST to the existing agentmemory REST surface; every script always emits a valid, non-cancelling `HookOutput` and swallows all errors (including 401), so Cline is unaffected when agentmemory is down or unauthenticated.

**Tech Stack:** TypeScript, Node 20 (`fetch`, `AbortSignal.timeout`), tsdown (bundler), vitest (tests), PowerShell + POSIX sh (installers).

**Reference spec:** `docs/superpowers/specs/2026-06-07-cline-hooks-adapter-design.md`

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/hooks/cline/_cline.ts` | Shared types, config/secret resolution, auth headers, stdin/stdout, REST helpers (`post`/`postDetached`), `taskId`→session + `workspaceRoots`→cwd mapping, file-path extraction, search rendering, the injected instructions block. Dependency-injected `Ctx` for testability. |
| `src/hooks/cline/task-start.ts` | `TaskStart` → `/session/start`, inject context + instructions. |
| `src/hooks/cline/task-resume.ts` | `TaskResume` → `/session/start` + `/context`, inject. |
| `src/hooks/cline/pre-tool-use.ts` | `PreToolUse` → `/enrich` on file params, inject. Never cancels. |
| `src/hooks/cline/post-tool-use.ts` | `PostToolUse` → `/observe` (success or failure). |
| `src/hooks/cline/prompt-submit.ts` | `UserPromptSubmit` → `/observe`; optional `/smart-search` inject (env-gated). |
| `src/hooks/cline/pre-compact.ts` | `PreCompact` → `/summarize` + `/context`, inject. |
| `src/hooks/cline/task-complete.ts` | `TaskComplete` → `/summarize` + `/session/end` + detached consolidate/crystals. |
| `src/hooks/cline/task-cancel.ts` | `TaskCancel` → `/observe` + `/session/end`. |
| `src/cli/connect/cline-hooks.ts` | Canonical hook→script map + shim/wrapper text builders (tested source of truth for installers). |
| `integrations/cline/install.ps1` | Windows installer: copy compiled scripts, write `config.json`, write `.ps1` shims. |
| `integrations/cline/install.sh` | POSIX installer: copy scripts, write `config.json` (0600), write executable wrappers. |
| `integrations/cline/README.md` | What it does, hook table, install/uninstall, env, auth, troubleshooting. |
| `tsdown.config.ts` | Add 8 cline entries → `plugin/cline/scripts/`. |
| `test/cline-hooks.test.ts` | Unit tests for `_cline.ts` (auth/config/mapping/render) + each hook's `run()`. |
| `test/cline-install.test.ts` | Unit tests for `cline-hooks.ts` map + shim builders. |

---

## Task 1: Shared `_cline.ts` module — config, auth, REST, mapping (the AUTH task)

**Files:**
- Create: `src/hooks/cline/_cline.ts`
- Test: `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing auth/config tests**

Create `test/cline-hooks.test.ts`:

```ts
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  authHeaders,
  resolveConfig,
  buildOutput,
  sessionIdOf,
  cwdOf,
  extractFilePaths,
  renderSearchResults,
  post,
  type Config,
} from "../src/hooks/cline/_cline.js";

describe("authHeaders", () => {
  it("attaches Bearer header when a secret is present", () => {
    expect(authHeaders("s3cr3t")).toEqual({
      "Content-Type": "application/json",
      Authorization: "Bearer s3cr3t",
    });
  });
  it("omits Authorization when no secret (open local deployment)", () => {
    expect(authHeaders("")).toEqual({ "Content-Type": "application/json" });
  });
});

describe("resolveConfig", () => {
  const OLD = { ...process.env };
  afterEach(() => {
    process.env = { ...OLD };
  });

  it("prefers env vars per-field", () => {
    process.env.AGENTMEMORY_URL = "http://host:9000";
    process.env.AGENTMEMORY_SECRET = "envsecret";
    expect(resolveConfig("/nonexistent/dir")).toEqual({
      url: "http://host:9000",
      secret: "envsecret",
    });
  });

  it("falls back to config.json for missing fields", () => {
    delete process.env.AGENTMEMORY_URL;
    delete process.env.AGENTMEMORY_SECRET;
    const dir = mkdtempSync(join(tmpdir(), "cline-cfg-"));
    try {
      writeFileSync(
        join(dir, "config.json"),
        JSON.stringify({ url: "http://file:1", secret: "filesecret" }),
      );
      expect(resolveConfig(dir)).toEqual({ url: "http://file:1", secret: "filesecret" });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("defaults url to localhost:3111 and secret to empty when nothing is set", () => {
    delete process.env.AGENTMEMORY_URL;
    delete process.env.AGENTMEMORY_SECRET;
    expect(resolveConfig("/nonexistent/dir")).toEqual({
      url: "http://localhost:3111",
      secret: "",
    });
  });
});

describe("post swallows auth/transport failures", () => {
  const cfg: Config = { url: "http://x", secret: "tok" };
  afterEach(() => vi.unstubAllGlobals());

  it("returns null on 401 (unauthorized)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 401 })));
    expect(await post(cfg, "/observe", {}, 1000)).toBeNull();
  });
  it("sends the Bearer header", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ context: "c" }) }));
    vi.stubGlobal("fetch", fetchMock);
    await post(cfg, "/context", { a: 1 }, 1000);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });
  it("returns null when fetch throws (server down)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("ECONNREFUSED"); }));
    expect(await post(cfg, "/observe", {}, 1000)).toBeNull();
  });
});

describe("input mapping", () => {
  it("maps taskId to sessionId", () => {
    expect(sessionIdOf({ taskId: "t-1" })).toBe("t-1");
  });
  it("synthesizes a session id when taskId missing", () => {
    expect(sessionIdOf({})).toMatch(/^cline_/);
  });
  it("uses workspaceRoots[0] as cwd", () => {
    expect(cwdOf({ workspaceRoots: ["/repo/a", "/repo/b"] })).toBe("/repo/a");
  });
  it("extracts known file-path keys from tool parameters", () => {
    expect(
      extractFilePaths({ file_path: "a.ts", path: "b.ts", other: "x", pattern: "*.ts" }),
    ).toEqual(["a.ts", "b.ts", "*.ts"]);
  });
});

describe("renderSearchResults", () => {
  it("renders compact results as a tagged title list", () => {
    const out = renderSearchResults("auth bug", [
      { obsId: "1", sessionId: "s", title: "401 on hooks", type: "bug", score: 0.9, timestamp: "t" },
    ]);
    expect(out).toContain("agentmemory-recall");
    expect(out).toContain("[bug] 401 on hooks");
  });
  it("returns empty string for no results", () => {
    expect(renderSearchResults("q", [])).toBe("");
  });
});

describe("buildOutput always safe", () => {
  it("forces cancel false and fills defaults", () => {
    expect(buildOutput({ contextModification: "x" })).toEqual({
      cancel: false,
      contextModification: "x",
      errorMessage: "",
    });
  });
  it("ignores any cancel passed in", () => {
    expect(buildOutput({ cancel: true } as never).cancel).toBe(false);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npx vitest run test/cline-hooks.test.ts`
Expected: FAIL — cannot resolve `../src/hooks/cline/_cline.js` (module does not exist yet).

- [ ] **Step 3: Implement `_cline.ts`**

Create `src/hooks/cline/_cline.ts`:

```ts
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { resolveProject } from "../_project.js";

export interface HookInput {
  clineVersion?: string;
  hookName?: string;
  timestamp?: string;
  taskId?: string;
  workspaceRoots?: string[];
  userId?: string;
  tool?: string;
  parameters?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  durationMs?: number;
  prompt?: string;
  attachments?: unknown[];
  [k: string]: unknown;
}

export interface HookOutput {
  cancel: boolean;
  contextModification: string;
  errorMessage: string;
}

export interface Config {
  url: string;
  secret: string;
}

export interface CompactResult {
  title: string;
  type: string;
  [k: string]: unknown;
}

const DEFAULT_URL = "http://localhost:3111";

export function authHeaders(secret: string): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (secret) h["Authorization"] = `Bearer ${secret}`;
  return h;
}

// Env wins per-field; config.json (written next to the compiled scripts by the
// installer) fills any gaps. `configDir` is injectable for tests; production
// callers pass the script's own directory.
export function resolveConfig(configDir: string): Config {
  let url = process.env["AGENTMEMORY_URL"] || "";
  let secret = process.env["AGENTMEMORY_SECRET"] || "";
  if (!url || !secret) {
    try {
      const raw = readFileSync(join(configDir, "config.json"), "utf-8");
      const file = JSON.parse(raw) as Partial<Config>;
      if (!url && typeof file.url === "string") url = file.url;
      if (!secret && typeof file.secret === "string") secret = file.secret;
    } catch {
      /* no config file — fine */
    }
  }
  return { url: url || DEFAULT_URL, secret };
}

export function loadConfig(): Config {
  return resolveConfig(dirname(fileURLToPath(import.meta.url)));
}

export function sessionIdOf(input: HookInput): string {
  return input.taskId || `cline_${Date.now().toString(36)}`;
}

export function cwdOf(input: HookInput): string {
  const roots = input.workspaceRoots;
  if (Array.isArray(roots) && roots.length > 0 && typeof roots[0] === "string") {
    return roots[0];
  }
  return process.cwd();
}

const FILE_KEYS = ["filePath", "file_path", "path", "file", "pattern"];

export function extractFilePaths(parameters: Record<string, unknown> | undefined): string[] {
  if (!parameters) return [];
  const files: string[] = [];
  for (const key of FILE_KEYS) {
    const v = parameters[key];
    if (typeof v === "string" && v.length > 0) files.push(v);
  }
  return files;
}

export function truncate(value: unknown, max: number): unknown {
  if (typeof value === "string") {
    return value.length > max ? value.slice(0, max) + "\n[...truncated]" : value;
  }
  if (value && typeof value === "object") {
    const str = JSON.stringify(value);
    return str.length > max ? str.slice(0, max) + "...[truncated]" : value;
  }
  return value;
}

export function renderSearchResults(query: string, results: CompactResult[]): string {
  if (!Array.isArray(results) || results.length === 0) return "";
  const lines = results
    .slice(0, 8)
    .map((r) => `- [${r.type}] ${r.title}`)
    .join("\n");
  return `<agentmemory-recall query="${query.slice(0, 80)}">\n${lines}\n</agentmemory-recall>`;
}

export const CLINE_INSTRUCTIONS = `<agentmemory>
You have persistent memory via the "agentmemory" MCP server. Use it proactively:
memory_save (remember a decision/bug/convention), memory_recall / memory_smart_search
(retrieve past context), memory_file_history (a file's past pitfalls before editing),
memory_lesson_save / memory_lesson_recall. Memory is also captured automatically by hooks.
</agentmemory>`;

export function buildOutput(partial: Partial<HookOutput>): HookOutput {
  return {
    cancel: false, // adapter never blocks
    contextModification: partial.contextModification ?? "",
    errorMessage: partial.errorMessage ?? "",
  };
}

export async function readInput(): Promise<HookInput | null> {
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  try {
    return JSON.parse(raw) as HookInput;
  } catch {
    return null;
  }
}

let emitted = false;
export function emit(partial: Partial<HookOutput> = {}): void {
  if (emitted) return;
  emitted = true;
  process.stdout.write(JSON.stringify(buildOutput(partial)));
}

// Safety net: if anything hangs, emit a valid no-op and exit well under Cline's 30s.
export function registerHardTimeout(ms = 5000): void {
  setTimeout(() => {
    emit();
    process.exit(0);
  }, ms).unref();
}

// Give detached (fire-and-forget) POSTs a brief window, then exit.
export function finishDetached(ms = 600): void {
  setTimeout(() => process.exit(0), ms).unref();
}

export async function post(
  cfg: Config,
  path: string,
  body: unknown,
  timeoutMs: number,
): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(`${cfg.url}/agentmemory${path}`, {
      method: "POST",
      headers: authHeaders(cfg.secret),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) return null;
    return (await res.json().catch(() => null)) as Record<string, unknown> | null;
  } catch {
    return null;
  }
}

export function postDetached(cfg: Config, path: string, body: unknown, timeoutMs: number): void {
  fetch(`${cfg.url}/agentmemory${path}`, {
    method: "POST",
    headers: authHeaders(cfg.secret),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  }).catch(() => {});
}

// Dependency-injected context so hook `run()` functions are unit-testable.
export interface Ctx {
  cfg: Config;
  post(path: string, body: unknown, timeoutMs: number): Promise<Record<string, unknown> | null>;
  postDetached(path: string, body: unknown, timeoutMs: number): void;
}

export function makeCtx(cfg: Config): Ctx {
  return {
    cfg,
    post: (p, b, t) => post(cfg, p, b, t),
    postDetached: (p, b, t) => postDetached(cfg, p, b, t),
  };
}

// Shared observe payload builder (whitelisted fields, project-resolved).
export function observePayload(
  input: HookInput,
  hookType: string,
  data: Record<string, unknown>,
): Record<string, unknown> {
  const cwd = cwdOf(input);
  return {
    hookType,
    sessionId: sessionIdOf(input),
    project: resolveProject(cwd),
    cwd,
    timestamp: new Date().toISOString(),
    data,
  };
}

export function contextString(result: Record<string, unknown> | null): string {
  return result && typeof result.context === "string" ? result.context : "";
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run test/cline-hooks.test.ts`
Expected: PASS (all auth/config/mapping/render/output cases).

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/_cline.ts test/cline-hooks.test.ts
git commit -m "feat(cline): shared hook module with auth + config resolution"
```

---

## Task 2: `TaskStart` hook — recall injection

**Files:**
- Create: `src/hooks/cline/task-start.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

Append to `test/cline-hooks.test.ts`:

```ts
import { run as runTaskStart } from "../src/hooks/cline/task-start.js";
import type { Ctx } from "../src/hooks/cline/_cline.js";

function fakeCtx(overrides: Partial<Record<string, unknown>> = {}) {
  const calls: Array<{ path: string; body: unknown }> = [];
  const ctx: Ctx = {
    cfg: { url: "http://x", secret: "t" },
    post: async (path, body) => {
      calls.push({ path, body });
      return (overrides[path] as Record<string, unknown>) ?? null;
    },
    postDetached: (path, body) => {
      calls.push({ path, body });
    },
  };
  return { ctx, calls };
}

describe("TaskStart run", () => {
  it("registers the session and injects returned context + instructions", async () => {
    const { ctx, calls } = fakeCtx({ "/session/start": { context: "PAST CONTEXT" } });
    const out = await runTaskStart({ taskId: "t1", workspaceRoots: ["/repo"] }, ctx);
    expect(calls[0].path).toBe("/session/start");
    expect((calls[0].body as Record<string, unknown>).sessionId).toBe("t1");
    expect(out.cancel).toBe(false);
    expect(out.contextModification).toContain("PAST CONTEXT");
    expect(out.contextModification).toContain("agentmemory");
  });

  it("still returns instructions (non-cancelling) when the server is down", async () => {
    const { ctx } = fakeCtx(); // /session/start → null
    const out = await runTaskStart({ taskId: "t1", workspaceRoots: ["/repo"] }, ctx);
    expect(out.cancel).toBe(false);
    expect(out.contextModification).toContain("agentmemory");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskStart run"`
Expected: FAIL — cannot resolve `task-start.js`.

- [ ] **Step 3: Implement `task-start.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, cwdOf, contextString, CLINE_INSTRUCTIONS,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const cwd = cwdOf(input);
  const result = await ctx.post("/session/start", {
    sessionId: sessionIdOf(input),
    project: resolveProject(cwd),
    cwd,
  }, 2500);
  const ctxText = contextString(result);
  const injection = [CLINE_INSTRUCTIONS, ctxText].filter(Boolean).join("\n\n");
  return { cancel: false, contextModification: injection, errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskStart run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/task-start.ts test/cline-hooks.test.ts
git commit -m "feat(cline): TaskStart hook injects recalled context"
```

---

## Task 3: `TaskResume` hook — re-inject context

**Files:**
- Create: `src/hooks/cline/task-resume.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runTaskResume } from "../src/hooks/cline/task-resume.js";

describe("TaskResume run", () => {
  it("re-registers the session then injects /context", async () => {
    const { ctx, calls } = fakeCtx({ "/context": { context: "RESUMED CONTEXT" } });
    const out = await runTaskResume({ taskId: "t2", workspaceRoots: ["/repo"] }, ctx);
    expect(calls.map((c) => c.path)).toEqual(["/session/start", "/context"]);
    expect(out.contextModification).toBe("RESUMED CONTEXT");
    expect(out.cancel).toBe(false);
  });

  it("returns empty non-cancelling output when context is unavailable", async () => {
    const { ctx } = fakeCtx();
    const out = await runTaskResume({ taskId: "t2", workspaceRoots: ["/repo"] }, ctx);
    expect(out).toEqual({ cancel: false, contextModification: "", errorMessage: "" });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskResume run"`
Expected: FAIL — cannot resolve `task-resume.js`.

- [ ] **Step 3: Implement `task-resume.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, cwdOf, contextString,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const cwd = cwdOf(input);
  const project = resolveProject(cwd);
  const sessionId = sessionIdOf(input);
  await ctx.post("/session/start", { sessionId, project, cwd }, 2000);
  const result = await ctx.post("/context", { sessionId, project }, 2500);
  return { cancel: false, contextModification: contextString(result), errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskResume run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/task-resume.ts test/cline-hooks.test.ts
git commit -m "feat(cline): TaskResume hook re-injects session context"
```

---

## Task 4: `PreToolUse` hook — file enrich injection (never cancels)

**Files:**
- Create: `src/hooks/cline/pre-tool-use.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runPreTool } from "../src/hooks/cline/pre-tool-use.js";

describe("PreToolUse run", () => {
  it("enriches with file history and injects it, never cancelling", async () => {
    const { ctx, calls } = fakeCtx({ "/enrich": { context: "FILE PITFALLS" } });
    const out = await runPreTool(
      { taskId: "t3", workspaceRoots: ["/repo"], tool: "write_to_file", parameters: { path: "a.ts" } },
      ctx,
    );
    expect(calls[0].path).toBe("/enrich");
    expect((calls[0].body as Record<string, unknown>).files).toEqual(["a.ts"]);
    expect(out.contextModification).toBe("FILE PITFALLS");
    expect(out.cancel).toBe(false);
  });

  it("no-ops (no network) when the tool has no file paths", async () => {
    const { ctx, calls } = fakeCtx();
    const out = await runPreTool(
      { taskId: "t3", workspaceRoots: ["/repo"], tool: "ask_followup_question", parameters: { question: "?" } },
      ctx,
    );
    expect(calls).toHaveLength(0);
    expect(out).toEqual({ cancel: false, contextModification: "", errorMessage: "" });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "PreToolUse run"`
Expected: FAIL — cannot resolve `pre-tool-use.js`.

- [ ] **Step 3: Implement `pre-tool-use.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, extractFilePaths, contextString,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const files = extractFilePaths(input.parameters);
  if (files.length === 0) {
    return { cancel: false, contextModification: "", errorMessage: "" };
  }
  const result = await ctx.post("/enrich", {
    sessionId: sessionIdOf(input),
    files: files.slice(0, 10),
    toolName: input.tool ?? "enrich_inject",
  }, 2500);
  return { cancel: false, contextModification: contextString(result), errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "PreToolUse run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/pre-tool-use.ts test/cline-hooks.test.ts
git commit -m "feat(cline): PreToolUse hook injects file history via enrich"
```

---

## Task 5: `PostToolUse` hook — capture (success/failure)

**Files:**
- Create: `src/hooks/cline/post-tool-use.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runPostTool } from "../src/hooks/cline/post-tool-use.js";

describe("PostToolUse run", () => {
  it("observes a successful tool call with timing", async () => {
    const { ctx, calls } = fakeCtx();
    const out = await runPostTool(
      { taskId: "t4", workspaceRoots: ["/repo"], tool: "read_file",
        parameters: { path: "a.ts" }, result: "ok", success: true, durationMs: 12 },
      ctx,
    );
    expect(calls[0].path).toBe("/observe");
    const body = calls[0].body as Record<string, unknown>;
    expect(body.hookType).toBe("post_tool_use");
    expect((body.data as Record<string, unknown>).duration_ms).toBe(12);
    expect(out.cancel).toBe(false);
  });

  it("routes failures to post_tool_failure", async () => {
    const { ctx, calls } = fakeCtx();
    await runPostTool(
      { taskId: "t4", workspaceRoots: ["/repo"], tool: "execute_command", result: "boom", success: false },
      ctx,
    );
    expect((calls[0].body as Record<string, unknown>).hookType).toBe("post_tool_failure");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "PostToolUse run"`
Expected: FAIL — cannot resolve `post-tool-use.js`.

- [ ] **Step 3: Implement `post-tool-use.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, truncate,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const success = input.success !== false;
  ctx.postDetached("/observe", observePayload(
    input,
    success ? "post_tool_use" : "post_tool_failure",
    {
      tool_name: input.tool,
      tool_input: truncate(input.parameters, 4000),
      tool_output: truncate(input.result, 8000),
      duration_ms: typeof input.durationMs === "number" ? input.durationMs : null,
    },
  ), 3000);
  return { cancel: false, contextModification: "", errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
  finishDetached();
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "PostToolUse run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/post-tool-use.ts test/cline-hooks.test.ts
git commit -m "feat(cline): PostToolUse hook captures tool outcomes"
```

---

## Task 6: `UserPromptSubmit` hook — observe + optional recall

**Files:**
- Create: `src/hooks/cline/prompt-submit.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runPrompt } from "../src/hooks/cline/prompt-submit.js";

describe("UserPromptSubmit run", () => {
  it("observes the prompt and does not inject by default", async () => {
    const { ctx, calls } = fakeCtx();
    const out = await runPrompt(
      { taskId: "t5", workspaceRoots: ["/repo"], prompt: "fix the auth bug", attachments: [] },
      ctx,
      false, // injectOnPrompt
    );
    expect(calls).toHaveLength(1);
    expect(calls[0].path).toBe("/observe");
    expect((calls[0].body as Record<string, unknown>).hookType).toBe("prompt_submit");
    expect(out.contextModification).toBe("");
  });

  it("injects rendered smart-search results when enabled", async () => {
    const { ctx, calls } = fakeCtx({
      "/smart-search": {
        mode: "compact",
        results: [{ title: "401 on hooks", type: "bug", obsId: "1", sessionId: "s", score: 1, timestamp: "t" }],
      },
    });
    const out = await runPrompt(
      { taskId: "t5", workspaceRoots: ["/repo"], prompt: "auth bug" },
      ctx,
      true,
    );
    expect(calls.map((c) => c.path)).toEqual(["/observe", "/smart-search"]);
    expect(out.contextModification).toContain("[bug] 401 on hooks");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "UserPromptSubmit run"`
Expected: FAIL — cannot resolve `prompt-submit.js`.

- [ ] **Step 3: Implement `prompt-submit.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, sessionIdOf, cwdOf, renderSearchResults,
  type HookInput, type HookOutput, type Ctx, type CompactResult,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx, injectOnPrompt: boolean): Promise<HookOutput> {
  const prompt = typeof input.prompt === "string" ? input.prompt : "";
  ctx.postDetached("/observe", observePayload(input, "prompt_submit", {
    prompt: prompt.slice(0, 8000),
    attachments: Array.isArray(input.attachments) ? input.attachments.length : 0,
  }), 3000);

  if (!injectOnPrompt || !prompt) {
    return { cancel: false, contextModification: "", errorMessage: "" };
  }
  const result = await ctx.post("/smart-search", {
    query: prompt,
    sessionId: sessionIdOf(input),
    project: resolveProject(cwdOf(input)),
    limit: 8,
  }, 2500);
  const results = (result?.results as CompactResult[] | undefined) ?? [];
  return {
    cancel: false,
    contextModification: renderSearchResults(prompt, results),
    errorMessage: "",
  };
}

const INJECT = process.env["AGENTMEMORY_INJECT_ON_PROMPT"] === "true";

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig()), INJECT));
  if (!INJECT) finishDetached();
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "UserPromptSubmit run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/prompt-submit.ts test/cline-hooks.test.ts
git commit -m "feat(cline): UserPromptSubmit hook observes prompt + optional recall"
```

---

## Task 7: `PreCompact` hook — summarize + inject before compaction

**Files:**
- Create: `src/hooks/cline/pre-compact.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runPreCompact } from "../src/hooks/cline/pre-compact.js";

describe("PreCompact run", () => {
  it("summarizes then injects fresh context to survive compaction", async () => {
    const { ctx, calls } = fakeCtx({ "/context": { context: "SURVIVING CONTEXT" } });
    const out = await runPreCompact({ taskId: "t6", workspaceRoots: ["/repo"] }, ctx);
    expect(calls.map((c) => c.path)).toEqual(["/summarize", "/context"]);
    expect(out.contextModification).toBe("SURVIVING CONTEXT");
    expect(out.cancel).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "PreCompact run"`
Expected: FAIL — cannot resolve `pre-compact.js`.

- [ ] **Step 3: Implement `pre-compact.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, cwdOf, contextString,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const sessionId = sessionIdOf(input);
  const project = resolveProject(cwdOf(input));
  await ctx.post("/summarize", { sessionId }, 2500);
  const result = await ctx.post("/context", { sessionId, project }, 2500);
  return { cancel: false, contextModification: contextString(result), errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "PreCompact run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/pre-compact.ts test/cline-hooks.test.ts
git commit -m "feat(cline): PreCompact hook preserves memory across compaction"
```

---

## Task 8: `TaskComplete` hook — summarize, end, consolidate

**Files:**
- Create: `src/hooks/cline/task-complete.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runTaskComplete } from "../src/hooks/cline/task-complete.js";

describe("TaskComplete run", () => {
  it("summarizes, ends the session, and fires consolidation detached", async () => {
    const { ctx, calls } = fakeCtx();
    const out = await runTaskComplete({ taskId: "t7", workspaceRoots: ["/repo"] }, ctx);
    const paths = calls.map((c) => c.path);
    expect(paths).toContain("/summarize");
    expect(paths).toContain("/session/end");
    expect(paths).toContain("/consolidate-pipeline");
    expect(paths).toContain("/crystals/auto");
    expect(out.cancel).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskComplete run"`
Expected: FAIL — cannot resolve `task-complete.js`.

- [ ] **Step 3: Implement `task-complete.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  sessionIdOf,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const sessionId = sessionIdOf(input);
  await ctx.post("/summarize", { sessionId }, 2500);
  await ctx.post("/session/end", { sessionId }, 2500);
  // Heavy maintenance — fire-and-forget, generous timeout.
  ctx.postDetached("/consolidate-pipeline", { tier: "all", force: true }, 30000);
  ctx.postDetached("/crystals/auto", { olderThanDays: 7 }, 30000);
  return { cancel: false, contextModification: "", errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
  finishDetached(800);
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskComplete run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/task-complete.ts test/cline-hooks.test.ts
git commit -m "feat(cline): TaskComplete hook summarizes, ends, consolidates"
```

---

## Task 9: `TaskCancel` hook — observe + end (no consolidate)

**Files:**
- Create: `src/hooks/cline/task-cancel.ts`
- Test: append to `test/cline-hooks.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { run as runTaskCancel } from "../src/hooks/cline/task-cancel.js";

describe("TaskCancel run", () => {
  it("observes the cancel and ends the session without consolidating", async () => {
    const { ctx, calls } = fakeCtx();
    const out = await runTaskCancel({ taskId: "t8", workspaceRoots: ["/repo"] }, ctx);
    const paths = calls.map((c) => c.path);
    expect(paths).toContain("/observe");
    expect(paths).toContain("/session/end");
    expect(paths).not.toContain("/consolidate-pipeline");
    expect(out.cancel).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskCancel run"`
Expected: FAIL — cannot resolve `task-cancel.js`.

- [ ] **Step 3: Implement `task-cancel.ts`**

```ts
#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, sessionIdOf,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  ctx.postDetached("/observe", observePayload(input, "task_cancel", {}), 3000);
  await ctx.post("/session/end", { sessionId: sessionIdOf(input) }, 2500);
  return { cancel: false, contextModification: "", errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
  finishDetached();
}

main().catch(() => emit());
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-hooks.test.ts -t "TaskCancel run"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/cline/task-cancel.ts test/cline-hooks.test.ts
git commit -m "feat(cline): TaskCancel hook ends session on cancellation"
```

---

## Task 10: Build integration — compile to `plugin/cline/scripts/`

**Files:**
- Modify: `tsdown.config.ts:3-17` (hook entry list) and `tsdown.config.ts:73-79` (output blocks)

- [ ] **Step 1: Add a Cline hook-entry list to `tsdown.config.ts`**

After the existing `hookEntries` array (ends at line 17), add:

```ts
const clineHookEntries = [
  "src/hooks/cline/task-start.ts",
  "src/hooks/cline/task-resume.ts",
  "src/hooks/cline/task-cancel.ts",
  "src/hooks/cline/task-complete.ts",
  "src/hooks/cline/pre-tool-use.ts",
  "src/hooks/cline/post-tool-use.ts",
  "src/hooks/cline/prompt-submit.ts",
  "src/hooks/cline/pre-compact.ts",
];
```

- [ ] **Step 2: Add output blocks for the Cline entries**

In the `defineConfig([...])` array, after the existing `...hookEntries.map((entry) => ({ ... outDir: "plugin/scripts" ... }))` block (ends ~line 79), add a new block (one entry per block, same anti-hoisting reason as the existing hooks):

```ts
  ...clineHookEntries.map((entry) => ({
    entry: [entry],
    outDir: "plugin/cline/scripts",
    ...shared,
    clean: false,
    sourcemap: false,
  })),
```

- [ ] **Step 3: Build and verify the compiled scripts exist**

Run: `npx tsdown`
Expected: build succeeds; then:

Run: `node -e "const f=require('fs');const want=['task-start','task-resume','task-cancel','task-complete','pre-tool-use','post-tool-use','prompt-submit','pre-compact'];const got=want.filter(n=>f.existsSync('plugin/cline/scripts/'+n+'.mjs'));console.log(got.length===8?'OK all 8':'MISSING '+want.filter(n=>!got.includes(n)));"`
Expected: `OK all 8`

- [ ] **Step 4: Smoke-test a compiled script end-to-end (stdin → stdout)**

Run (PowerShell): `'{"taskId":"smoke","workspaceRoots":["."]}' | node plugin/cline/scripts/task-start.mjs`
Expected: a single line of JSON containing `"cancel":false` and `"contextModification"` (the `<agentmemory>` block at minimum; context too if the server is running). It must NOT error even if agentmemory is down.

- [ ] **Step 5: Commit**

```bash
git add tsdown.config.ts plugin/cline/scripts
git commit -m "build(cline): compile cline hooks to plugin/cline/scripts"
```

---

## Task 11: Installer + shim builders (`cline-hooks.ts`, `install.ps1`, `install.sh`)

**Files:**
- Create: `src/cli/connect/cline-hooks.ts`
- Create: `integrations/cline/install.ps1`
- Create: `integrations/cline/install.sh`
- Test: `test/cline-install.test.ts`

- [ ] **Step 1: Write the failing test for the canonical map + shim builders**

Create `test/cline-install.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
import { CLINE_HOOKS, buildPwshShim, buildPosixWrapper } from "../src/cli/connect/cline-hooks.js";

describe("CLINE_HOOKS map", () => {
  it("covers all eight Cline hook types", () => {
    expect(CLINE_HOOKS.map((h) => h.hookName).sort()).toEqual(
      ["PostToolUse", "PreCompact", "PreToolUse", "TaskCancel", "TaskComplete", "TaskResume", "TaskStart", "UserPromptSubmit"].sort(),
    );
  });

  it("points every hook at a compiled script that exists", () => {
    for (const h of CLINE_HOOKS) {
      const p = resolve(__dirname, "..", "plugin", "cline", "scripts", h.scriptFile);
      expect(existsSync(p), `${h.scriptFile} should exist (run tsdown first)`).toBe(true);
    }
  });
});

describe("shim builders", () => {
  it("pwsh shim reads stdin and pipes to node with the matching script", () => {
    const shim = buildPwshShim("task-start.mjs");
    expect(shim).toContain("[Console]::In.ReadToEnd()");
    expect(shim).toContain("node");
    expect(shim).toContain(".agentmemory\\task-start.mjs");
  });

  it("posix wrapper is a node-shebang passthrough to the matching script", () => {
    const w = buildPosixWrapper("task-start.mjs");
    expect(w.startsWith("#!/usr/bin/env")).toBe(true);
    expect(w).toContain(".agentmemory/task-start.mjs");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx vitest run test/cline-install.test.ts`
Expected: FAIL — cannot resolve `cline-hooks.js`.

- [ ] **Step 3: Implement `src/cli/connect/cline-hooks.ts`**

```ts
// Canonical mapping of Cline hook types → compiled script files, plus the
// per-platform shim text. Source of truth for integrations/cline/install.*.
// Keep this list in sync with clineHookEntries in tsdown.config.ts.
export interface ClineHook {
  hookName: string; // Cline discovers a file named exactly this (+ .ps1 on Windows)
  scriptFile: string; // compiled .mjs under .agentmemory/
}

export const CLINE_HOOKS: ClineHook[] = [
  { hookName: "TaskStart", scriptFile: "task-start.mjs" },
  { hookName: "TaskResume", scriptFile: "task-resume.mjs" },
  { hookName: "TaskCancel", scriptFile: "task-cancel.mjs" },
  { hookName: "TaskComplete", scriptFile: "task-complete.mjs" },
  { hookName: "PreToolUse", scriptFile: "pre-tool-use.mjs" },
  { hookName: "PostToolUse", scriptFile: "post-tool-use.mjs" },
  { hookName: "UserPromptSubmit", scriptFile: "prompt-submit.mjs" },
  { hookName: "PreCompact", scriptFile: "pre-compact.mjs" },
];

export function buildPwshShim(scriptFile: string): string {
  return [
    "$ErrorActionPreference = 'SilentlyContinue'",
    "$stdin = [Console]::In.ReadToEnd()",
    `$stdin | node "$PSScriptRoot\\.agentmemory\\${scriptFile}"`,
    "",
  ].join("\r\n");
}

export function buildPosixWrapper(scriptFile: string): string {
  return [
    "#!/usr/bin/env bash",
    'DIR="$(cd "$(dirname "$0")" && pwd)"',
    `exec node "$DIR/.agentmemory/${scriptFile}"`,
    "",
  ].join("\n");
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx vitest run test/cline-install.test.ts`
Expected: PASS (requires Task 10's compiled scripts to be present).

- [ ] **Step 5: Implement `integrations/cline/install.ps1`**

```powershell
#Requires -Version 5.1
param(
  [string]$Project = "",
  [switch]$Uninstall
)
$ErrorActionPreference = "Stop"

# Repo root = two levels up from this script (integrations/cline/).
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ScriptsSrc = Join-Path $RepoRoot "plugin\cline\scripts"

if ($Project) {
  $HooksDir = Join-Path (Resolve-Path $Project) ".clinerules\hooks"
} else {
  $HooksDir = Join-Path $env:USERPROFILE "Documents\Cline\Rules\Hooks"
}
$AgentDir = Join-Path $HooksDir ".agentmemory"

# Hook type -> compiled script. Keep in sync with src/cli/connect/cline-hooks.ts.
$Hooks = [ordered]@{
  "TaskStart"        = "task-start.mjs"
  "TaskResume"       = "task-resume.mjs"
  "TaskCancel"       = "task-cancel.mjs"
  "TaskComplete"     = "task-complete.mjs"
  "PreToolUse"       = "pre-tool-use.mjs"
  "PostToolUse"      = "post-tool-use.mjs"
  "UserPromptSubmit" = "prompt-submit.mjs"
  "PreCompact"       = "pre-compact.mjs"
}

if ($Uninstall) {
  foreach ($name in $Hooks.Keys) {
    Remove-Item (Join-Path $HooksDir "$name.ps1") -Force -ErrorAction SilentlyContinue
  }
  Remove-Item $AgentDir -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "Uninstalled agentmemory Cline hooks from $HooksDir"
  exit 0
}

if (-not (Test-Path $ScriptsSrc)) { throw "Compiled scripts not found at $ScriptsSrc. Run 'npx tsdown' first." }

New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
Copy-Item (Join-Path $ScriptsSrc "*.mjs") $AgentDir -Force

# Resolve URL + secret: env first, then ~/.agentmemory/.env
$Url = if ($env:AGENTMEMORY_URL) { $env:AGENTMEMORY_URL } else { "http://localhost:3111" }
$Secret = $env:AGENTMEMORY_SECRET
$DotEnv = Join-Path $env:USERPROFILE ".agentmemory\.env"
if (-not $Secret -and (Test-Path $DotEnv)) {
  $line = Select-String -Path $DotEnv -Pattern '^\s*AGENTMEMORY_SECRET\s*=' | Select-Object -First 1
  if ($line) { $Secret = ($line.Line -replace '^\s*AGENTMEMORY_SECRET\s*=\s*', '').Trim('"').Trim("'") }
}
$SecretVal = if ($Secret) { $Secret } else { "" }
$Config = @{ url = $Url; secret = $SecretVal } | ConvertTo-Json -Compress
Set-Content -Path (Join-Path $AgentDir "config.json") -Value $Config -Encoding utf8 -NoNewline

foreach ($name in $Hooks.Keys) {
  $script = $Hooks[$name]
  $shim = "`$ErrorActionPreference = 'SilentlyContinue'`r`n`$stdin = [Console]::In.ReadToEnd()`r`n`$stdin | node `"`$PSScriptRoot\.agentmemory\$script`""
  Set-Content -Path (Join-Path $HooksDir "$name.ps1") -Value $shim -Encoding utf8
}

Write-Host "Installed agentmemory Cline hooks to $HooksDir"
Write-Host "Auth: $(if ($Secret) { 'Bearer secret configured' } else { 'no secret (open local deployment)' })"
```

- [ ] **Step 6: Implement `integrations/cline/install.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT=""
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --project=*) PROJECT="${arg#*=}" ;;
    --uninstall) UNINSTALL=1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPTS_SRC="$REPO_ROOT/plugin/cline/scripts"

if [ -n "$PROJECT" ]; then
  HOOKS_DIR="$(cd "$PROJECT" && pwd)/.clinerules/hooks"
else
  HOOKS_DIR="$HOME/Documents/Cline/Rules/Hooks"
fi
AGENT_DIR="$HOOKS_DIR/.agentmemory"

# Hook type -> compiled script. Keep in sync with src/cli/connect/cline-hooks.ts.
HOOKS="TaskStart:task-start.mjs TaskResume:task-resume.mjs TaskCancel:task-cancel.mjs \
TaskComplete:task-complete.mjs PreToolUse:pre-tool-use.mjs PostToolUse:post-tool-use.mjs \
UserPromptSubmit:prompt-submit.mjs PreCompact:pre-compact.mjs"

if [ "$UNINSTALL" -eq 1 ]; then
  for pair in $HOOKS; do rm -f "$HOOKS_DIR/${pair%%:*}"; done
  rm -rf "$AGENT_DIR"
  echo "Uninstalled agentmemory Cline hooks from $HOOKS_DIR"
  exit 0
fi

[ -d "$SCRIPTS_SRC" ] || { echo "Compiled scripts not found at $SCRIPTS_SRC. Run 'npx tsdown' first." >&2; exit 1; }

mkdir -p "$AGENT_DIR"
cp "$SCRIPTS_SRC"/*.mjs "$AGENT_DIR"/

URL="${AGENTMEMORY_URL:-http://localhost:3111}"
SECRET="${AGENTMEMORY_SECRET:-}"
DOTENV="$HOME/.agentmemory/.env"
if [ -z "$SECRET" ] && [ -f "$DOTENV" ]; then
  SECRET="$(grep -E '^\s*AGENTMEMORY_SECRET\s*=' "$DOTENV" | head -n1 | sed -E 's/^\s*AGENTMEMORY_SECRET\s*=\s*//' | tr -d '"'"'"' )"
fi
printf '{"url":"%s","secret":"%s"}' "$URL" "$SECRET" > "$AGENT_DIR/config.json"
chmod 600 "$AGENT_DIR/config.json"

for pair in $HOOKS; do
  name="${pair%%:*}"; script="${pair#*:}"
  cat > "$HOOKS_DIR/$name" <<EOF
#!/usr/bin/env bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec node "\$DIR/.agentmemory/$script"
EOF
  chmod +x "$HOOKS_DIR/$name"
done

echo "Installed agentmemory Cline hooks to $HOOKS_DIR"
[ -n "$SECRET" ] && echo "Auth: Bearer secret configured" || echo "Auth: no secret (open local deployment)"
```

- [ ] **Step 7: Run the full test file again**

Run: `npx vitest run test/cline-install.test.ts`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/cli/connect/cline-hooks.ts integrations/cline/install.ps1 integrations/cline/install.sh test/cline-install.test.ts
git commit -m "feat(cline): installer + shim builders for global/project hooks"
```

---

## Task 12: README + gitignore for the install artifact

**Files:**
- Create: `integrations/cline/README.md`
- Modify: `.gitignore` (append config.json ignore)

- [ ] **Step 1: Write `integrations/cline/README.md`**

```markdown
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
```

- [ ] **Step 2: Append the config.json ignore to `.gitignore`**

Add these lines to `.gitignore`:

```
# Cline hooks install artifact (holds the bearer secret)
**/Cline/Rules/Hooks/.agentmemory/config.json
.clinerules/hooks/.agentmemory/config.json
```

- [ ] **Step 3: Verify the ignore works**

Run: `git check-ignore -v .clinerules/hooks/.agentmemory/config.json`
Expected: prints the matching `.gitignore` rule (confirming it is ignored).

- [ ] **Step 4: Commit**

```bash
git add integrations/cline/README.md .gitignore
git commit -m "docs(cline): integration README + gitignore secret config"
```

---

## Task 13: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite for the new files**

Run: `npx vitest run test/cline-hooks.test.ts test/cline-install.test.ts`
Expected: PASS, all describe blocks green.

- [ ] **Step 2: Typecheck the new sources**

Run: `npx tsc --noEmit`
Expected: no errors in `src/hooks/cline/*` or `src/cli/connect/cline-hooks.ts`.

- [ ] **Step 3: Rebuild and re-verify compiled output**

Run: `npx tsdown`
Then: `node -e "const f=require('fs');['task-start','task-resume','task-cancel','task-complete','pre-tool-use','post-tool-use','prompt-submit','pre-compact'].forEach(n=>{if(!f.existsSync('plugin/cline/scripts/'+n+'.mjs'))throw new Error('missing '+n)});console.log('OK')"`
Expected: `OK`

- [ ] **Step 4: End-to-end install smoke test into a temp dir**

Run (PowerShell): `./integrations/cline/install.ps1 -Project $env:TEMP\cline-smoke`
Then verify: `Test-Path "$env:TEMP\cline-smoke\.clinerules\hooks\TaskStart.ps1"` → `True`,
and `Test-Path "$env:TEMP\cline-smoke\.clinerules\hooks\.agentmemory\config.json"` → `True`.
Then pipe a payload through the installed shim:
`'{"taskId":"smoke","workspaceRoots":["."]}' | pwsh "$env:TEMP\cline-smoke\.clinerules\hooks\TaskStart.ps1"`
Expected: one line of JSON with `"cancel":false`. Then clean up: `./integrations/cline/install.ps1 -Project $env:TEMP\cline-smoke -Uninstall`.

- [ ] **Step 5: Live manual check (requires the agentmemory container running)**

Install globally, open a project in Cline, run a short task, then confirm in the
viewer (`http://localhost:3113`) that a session started, observations landed for
the prompt + tool calls, and `TaskComplete` produced a summary. If nothing
appears, check auth: `node plugin/cline/scripts/task-start.mjs` with a payload
should not 401 — verify the secret in `.agentmemory/config.json` matches
`~/.agentmemory/.env`.

- [ ] **Step 6: Final commit (if any artifacts changed)**

```bash
git add -A
git commit -m "chore(cline): verification pass for hooks adapter"
```

---

## Self-Review Notes

- **Auth (the explicit ask):** Task 1 implements `authHeaders` + `resolveConfig`
  (env → `config.json`) with tests for Bearer presence/absence and 401/throw
  swallowing; Task 11 sources the secret from `~/.agentmemory/.env` into
  `config.json`; Task 12 documents the order and gitignores the secret. Covered.
- **Spec coverage:** all 8 hooks (Tasks 2–9), build (10), installer/global
  install (11), README (12), safety/never-block (every `run()` returns
  `cancel:false`; `emit` idempotent; `registerHardTimeout`). Observe-only
  default on prompts + env-gated recall (Task 6). All present.
- **Type consistency:** `Ctx`, `HookInput`, `HookOutput`, `Config`,
  `CompactResult`, `run(input, ctx)` signatures, and helper names
  (`resolveConfig`/`loadConfig`, `observePayload`, `contextString`,
  `renderSearchResults`, `extractFilePaths`, `finishDetached`,
  `registerHardTimeout`) are defined in Task 1 and used consistently thereafter.
- **No placeholders:** every code/test/command step contains complete content.
```
