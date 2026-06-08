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
