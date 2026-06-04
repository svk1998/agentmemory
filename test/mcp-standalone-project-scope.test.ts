import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { handleToolCall } from "../src/mcp/standalone.js";
import { resetHandleForTests } from "../src/mcp/rest-proxy.js";

function installFetch(handler: (url: string, init?: RequestInit) => Response) {
  const fn = vi.fn(async (url: string | URL, init?: RequestInit) =>
    handler(url.toString(), init),
  );
  (globalThis as { fetch: typeof fetch }).fetch = fn as unknown as typeof fetch;
  return fn;
}

const BASE = "http://localhost:3111";

describe("@agentmemory/mcp standalone — project-scoped recall parity", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    resetHandleForTests();
    process.env["AGENTMEMORY_URL"] = BASE;
    delete process.env["AGENTMEMORY_SECRET"];
  });

  afterEach(() => {
    resetHandleForTests();
    globalThis.fetch = originalFetch;
    delete process.env["AGENTMEMORY_URL"];
  });

  it("forwards project to POST /agentmemory/search for memory_recall", async () => {
    let body: Record<string, unknown> | undefined;
    installFetch((url, init) => {
      if (url.endsWith("/agentmemory/livez")) return new Response("ok", { status: 200 });
      if (url.endsWith("/agentmemory/search")) {
        body = init?.body ? JSON.parse(init.body as string) : undefined;
        return new Response(JSON.stringify({ mode: "full", facts: [] }), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    });
    await handleToolCall("memory_recall", { query: "auth", project: "acme-api" });
    expect(body?.["project"]).toBe("acme-api");
  });

  it("omits project from the /agentmemory/search body when not supplied", async () => {
    let body: Record<string, unknown> | undefined;
    installFetch((url, init) => {
      if (url.endsWith("/agentmemory/livez")) return new Response("ok", { status: 200 });
      if (url.endsWith("/agentmemory/search")) {
        body = init?.body ? JSON.parse(init.body as string) : undefined;
        return new Response(JSON.stringify({ mode: "full", facts: [] }), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    });
    await handleToolCall("memory_recall", { query: "auth" });
    expect(body).not.toHaveProperty("project");
  });

  it("forwards project to POST /agentmemory/smart-search for memory_smart_search", async () => {
    let body: Record<string, unknown> | undefined;
    installFetch((url, init) => {
      if (url.endsWith("/agentmemory/livez")) return new Response("ok", { status: 200 });
      if (url.endsWith("/agentmemory/smart-search")) {
        body = init?.body ? JSON.parse(init.body as string) : undefined;
        return new Response(JSON.stringify({ mode: "compact", results: [] }), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    });
    await handleToolCall("memory_smart_search", { query: "auth", project: "acme-api" });
    expect(body?.["project"]).toBe("acme-api");
  });
});
