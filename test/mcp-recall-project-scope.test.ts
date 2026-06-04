import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../src/logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import { registerMcpEndpoints } from "../src/mcp/server.js";
import { getAllTools } from "../src/mcp/tools-registry.js";

function mockKV() {
  const store = new Map<string, Map<string, unknown>>();
  return {
    get: async <T>(s: string, k: string): Promise<T | null> =>
      (store.get(s)?.get(k) as T) ?? null,
    set: async <T>(s: string, k: string, d: T): Promise<T> => {
      if (!store.has(s)) store.set(s, new Map());
      store.get(s)!.set(k, d);
      return d;
    },
    delete: async (s: string, k: string): Promise<void> => {
      store.get(s)?.delete(k);
    },
    list: async <T>(s: string): Promise<T[]> => {
      const e = store.get(s);
      return e ? (Array.from(e.values()) as T[]) : [];
    },
  };
}

function mockSdk() {
  const functions = new Map<string, Function>();
  const overrides = new Map<string, Function>();
  return {
    registerFunction: (idOrOpts: string | { id: string }, handler: Function) => {
      functions.set(typeof idOrOpts === "string" ? idOrOpts : idOrOpts.id, handler);
    },
    registerTrigger: () => {},
    trigger: async (
      idOrInput: string | { function_id: string; payload: unknown },
      data?: unknown,
    ) => {
      const id = typeof idOrInput === "string" ? idOrInput : idOrInput.function_id;
      const payload = typeof idOrInput === "string" ? data : idOrInput.payload;
      if (overrides.has(id)) return overrides.get(id)!(payload);
      const fn = functions.get(id);
      if (!fn) throw new Error(`No function: ${id}`);
      return fn(payload);
    },
    overrideTrigger: (id: string, handler: Function) => overrides.set(id, handler),
    getFunction: (id: string) => functions.get(id),
  };
}

function makeReq(body?: unknown) {
  return { body, headers: {}, query_params: {} };
}

describe("project-scoped MCP recall", () => {
  let sdk: ReturnType<typeof mockSdk>;

  beforeEach(() => {
    sdk = mockSdk();
    registerMcpEndpoints(sdk as never, mockKV() as never);
  });

  function toolSchema(name: string) {
    const tool = getAllTools().find((t) => t.name === name)!;
    return (tool.inputSchema as { properties: Record<string, unknown> }).properties;
  }

  it("exposes a project property on memory_recall", () => {
    expect(toolSchema("memory_recall")).toHaveProperty("project");
  });

  it("exposes a project property on memory_smart_search", () => {
    expect(toolSchema("memory_smart_search")).toHaveProperty("project");
  });

  it("forwards project to mem::search for memory_recall", async () => {
    let captured: Record<string, unknown> | undefined;
    sdk.overrideTrigger("mem::search", async (p: Record<string, unknown>) => {
      captured = p;
      return { results: [] };
    });
    const fn = sdk.getFunction("mcp::tools::call")!;
    await fn(
      makeReq({
        name: "memory_recall",
        arguments: { query: "auth flow", project: "acme-api" },
      }),
    );
    expect(captured?.project).toBe("acme-api");
  });

  it("omits project for memory_recall when not supplied (stays global)", async () => {
    let captured: Record<string, unknown> | undefined;
    sdk.overrideTrigger("mem::search", async (p: Record<string, unknown>) => {
      captured = p;
      return { results: [] };
    });
    const fn = sdk.getFunction("mcp::tools::call")!;
    await fn(makeReq({ name: "memory_recall", arguments: { query: "auth flow" } }));
    expect(captured?.project).toBeUndefined();
  });

  it("forwards project to mem::smart-search for memory_smart_search", async () => {
    let captured: Record<string, unknown> | undefined;
    sdk.overrideTrigger("mem::smart-search", async (p: Record<string, unknown>) => {
      captured = p;
      return { results: [] };
    });
    const fn = sdk.getFunction("mcp::tools::call")!;
    await fn(
      makeReq({
        name: "memory_smart_search",
        arguments: { query: "auth flow", project: "acme-api" },
      }),
    );
    expect(captured?.project).toBe("acme-api");
  });

  it("ignores a blank project string for memory_recall", async () => {
    let captured: Record<string, unknown> | undefined;
    sdk.overrideTrigger("mem::search", async (p: Record<string, unknown>) => {
      captured = p;
      return { results: [] };
    });
    const fn = sdk.getFunction("mcp::tools::call")!;
    await fn(
      makeReq({ name: "memory_recall", arguments: { query: "x", project: "   " } }),
    );
    expect(captured?.project).toBeUndefined();
  });
});
