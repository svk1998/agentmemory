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
