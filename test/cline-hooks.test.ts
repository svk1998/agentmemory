import { describe, it, expect, vi, afterEach } from "vitest";
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
  truncate,
  contextString,
  type Config,
} from "../src/hooks/cline/_cline.js";
import { run as runTaskStart } from "../src/hooks/cline/task-start.js";
import { run as runTaskResume } from "../src/hooks/cline/task-resume.js";
import { run as runPreTool } from "../src/hooks/cline/pre-tool-use.js";
import type { Ctx } from "../src/hooks/cline/_cline.js";

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

describe("resolveConfig mixed env + file", () => {
  const OLD = { ...process.env };
  afterEach(() => {
    process.env = { ...OLD };
  });

  it("takes url from env and secret from config.json", () => {
    process.env.AGENTMEMORY_URL = "http://env-url:1";
    delete process.env.AGENTMEMORY_SECRET;
    const dir = mkdtempSync(join(tmpdir(), "cline-cfg-mix-"));
    try {
      writeFileSync(
        join(dir, "config.json"),
        JSON.stringify({ url: "http://file-url:2", secret: "filesecret" }),
      );
      // env url wins; secret falls back to the file
      expect(resolveConfig(dir)).toEqual({ url: "http://env-url:1", secret: "filesecret" });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("truncate", () => {
  it("returns short strings unchanged", () => {
    expect(truncate("hi", 10)).toBe("hi");
  });
  it("truncates long strings with the newline suffix", () => {
    expect(truncate("abcdef", 3)).toBe("abc\n[...truncated]");
  });
  it("returns small objects unchanged", () => {
    const obj = { a: 1 };
    expect(truncate(obj, 100)).toBe(obj);
  });
  it("truncates oversized objects to a string with the object suffix", () => {
    const out = truncate({ a: "xxxxxxxxxx" }, 5);
    expect(typeof out).toBe("string");
    expect(out as string).toContain("...[truncated]");
  });
  it("passes through non-string/non-object values", () => {
    expect(truncate(42, 5)).toBe(42);
    expect(truncate(null, 5)).toBe(null);
  });
});

describe("contextString", () => {
  it("returns the context field when present and a string", () => {
    expect(contextString({ context: "hello" })).toBe("hello");
  });
  it("returns empty string for null or missing/non-string context", () => {
    expect(contextString(null)).toBe("");
    expect(contextString({})).toBe("");
    expect(contextString({ context: 123 })).toBe("");
  });
});

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
