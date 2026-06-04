import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../src/logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import { registerMcpEndpoints } from "../src/mcp/server.js";

type McpResponse = { status_code: number; headers?: Record<string, string>; body: unknown };

function mockKV() {
  const store = new Map<string, Map<string, unknown>>();
  return {
    get: async <T>(scope: string, key: string): Promise<T | null> =>
      (store.get(scope)?.get(key) as T) ?? null,
    set: async <T>(scope: string, key: string, data: T): Promise<T> => {
      if (!store.has(scope)) store.set(scope, new Map());
      store.get(scope)!.set(key, data);
      return data;
    },
    delete: async (scope: string, key: string): Promise<void> => {
      store.get(scope)?.delete(key);
    },
    list: async <T>(scope: string): Promise<T[]> => {
      const entries = store.get(scope);
      return entries ? (Array.from(entries.values()) as T[]) : [];
    },
  };
}

function mockSdk() {
  const functions = new Map<string, Function>();
  const triggerOverrides = new Map<string, Function>();
  return {
    registerFunction: (idOrOpts: string | { id: string }, handler: Function) => {
      const id = typeof idOrOpts === "string" ? idOrOpts : idOrOpts.id;
      functions.set(id, handler);
    },
    registerTrigger: () => {},
    trigger: async (
      idOrInput: string | { function_id: string; payload: unknown },
      data?: unknown,
    ) => {
      const id = typeof idOrInput === "string" ? idOrInput : idOrInput.function_id;
      const payload = typeof idOrInput === "string" ? data : idOrInput.payload;
      if (triggerOverrides.has(id)) return triggerOverrides.get(id)!(payload);
      const fn = functions.get(id);
      if (!fn) throw new Error(`No function: ${id}`);
      return fn(payload);
    },
    overrideTrigger: (id: string, handler: Function) => {
      triggerOverrides.set(id, handler);
    },
    getFunction: (id: string) => functions.get(id),
  };
}

function makeReq(body?: unknown, headers?: Record<string, string>) {
  return { body, headers: headers || {}, query_params: {} };
}

function rpc(id: number | string | null, method: string, params?: unknown) {
  return { jsonrpc: "2.0", id, method, ...(params !== undefined ? { params } : {}) };
}

describe("Streamable HTTP MCP endpoint (POST /agentmemory/mcp)", () => {
  let sdk: ReturnType<typeof mockSdk>;
  let kv: ReturnType<typeof mockKV>;

  beforeEach(() => {
    sdk = mockSdk();
    kv = mockKV();
    registerMcpEndpoints(sdk as never, kv as never);
  });

  function call(body: unknown, headers?: Record<string, string>): Promise<McpResponse> {
    const fn = sdk.getFunction("mcp::streamable")!;
    return fn(makeReq(body, headers)) as Promise<McpResponse>;
  }

  it("registers a POST trigger on /agentmemory/mcp", () => {
    expect(sdk.getFunction("mcp::streamable")).toBeTypeOf("function");
  });

  it("answers initialize with serverInfo and echoes the requested protocolVersion", async () => {
    const res = await call(rpc(1, "initialize", { protocolVersion: "2025-03-26" }));
    expect(res.status_code).toBe(200);
    expect(res.headers?.["Content-Type"]).toMatch(/application\/json/);
    const body = res.body as { jsonrpc: string; id: number; result: any };
    expect(body.jsonrpc).toBe("2.0");
    expect(body.id).toBe(1);
    expect(body.result.serverInfo.name).toBe("agentmemory");
    expect(body.result.protocolVersion).toBe("2025-03-26");
  });

  it("returns 202 with no JSON-RPC body for a notification", async () => {
    const res = await call({ jsonrpc: "2.0", method: "notifications/initialized" });
    expect(res.status_code).toBe(202);
    expect(res.body).toBe("");
  });

  it("lists tools as a JSON-RPC result", async () => {
    const res = await call(rpc(2, "tools/list"));
    const body = res.body as { result: { tools: Array<{ name: string }> } };
    expect(Array.isArray(body.result.tools)).toBe(true);
    expect(body.result.tools.length).toBeGreaterThan(0);
    expect(body.result.tools.some((t) => t.name === "memory_save")).toBe(true);
  });

  it("executes tools/call and returns the tool's content result", async () => {
    sdk.overrideTrigger?.("mem::remember", async () => ({ id: "mem_1", saved: true }));
    const res = await call(
      rpc(3, "tools/call", { name: "memory_save", arguments: { content: "hello world" } }),
    );
    expect(res.status_code).toBe(200);
    const body = res.body as { result: { content: Array<{ type: string; text: string }> } };
    expect(body.result.content[0].type).toBe("text");
    expect(body.result.content[0].text).toContain("mem_1");
  });

  it("surfaces a tool argument failure as an isError result, not a protocol error", async () => {
    const res = await call(rpc(4, "tools/call", { name: "memory_save", arguments: {} }));
    expect(res.status_code).toBe(200);
    const body = res.body as { result: { isError?: boolean }; error?: unknown };
    expect(body.error).toBeUndefined();
    expect(body.result.isError).toBe(true);
  });

  it("returns -32601 Method not found for an unknown method", async () => {
    const res = await call(rpc(5, "does/not/exist"));
    const body = res.body as { error: { code: number } };
    expect(body.error.code).toBe(-32601);
  });

  it("reads a resource via resources/read", async () => {
    const res = await call(rpc(6, "resources/read", { uri: "agentmemory://status" }));
    const body = res.body as { result: { contents: Array<{ uri: string }> } };
    expect(body.result.contents[0].uri).toBe("agentmemory://status");
  });

  it("processes a batch, returning one response per request and dropping notifications", async () => {
    const res = await call([
      rpc(10, "tools/list"),
      { jsonrpc: "2.0", method: "notifications/initialized" },
      rpc(11, "ping"),
    ]);
    expect(res.status_code).toBe(200);
    const body = res.body as Array<{ id: number }>;
    expect(body).toHaveLength(2);
    expect(body.map((r) => r.id).sort()).toEqual([10, 11]);
  });

  it("rejects with 401 when a secret is configured and no bearer is sent", async () => {
    const authedSdk = mockSdk();
    registerMcpEndpoints(authedSdk as never, mockKV() as never, "s3cret");
    const fn = authedSdk.getFunction("mcp::streamable")!;
    const unauthed = (await fn(makeReq(rpc(1, "tools/list")))) as McpResponse;
    expect(unauthed.status_code).toBe(401);
    const authed = (await fn(
      makeReq(rpc(1, "tools/list"), { authorization: "Bearer s3cret" }),
    )) as McpResponse;
    expect(authed.status_code).toBe(200);
  });
});
