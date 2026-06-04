import { describe, it, expect, vi } from "vitest";
import { createMcpMethodRouter, type McpMethodDeps } from "../src/mcp/mcp-methods.js";
import { RpcError } from "../src/mcp/transport.js";

function deps(overrides: Partial<McpMethodDeps> = {}): McpMethodDeps {
  return {
    serverInfo: { name: "agentmemory", version: "9.9.9", protocolVersion: "2024-11-05" },
    listTools: vi.fn(async () => ({ tools: [{ name: "memory_save" }] })),
    callTool: vi.fn(async (name: string) => ({ content: [{ type: "text", text: `ran ${name}` }] })),
    listResources: vi.fn(async () => ({ resources: [{ uri: "agentmemory://status" }] })),
    readResource: vi.fn(async (uri: string) => ({ contents: [{ uri, text: "x" }] })),
    listPrompts: vi.fn(async () => ({ prompts: [{ name: "recall_context" }] })),
    getPrompt: vi.fn(async (name: string) => ({ messages: [{ role: "user", name }] })),
    ...overrides,
  };
}

describe("createMcpMethodRouter", () => {
  it("initialize echoes the client's requested protocolVersion and advertises capabilities", async () => {
    const router = createMcpMethodRouter(deps());
    const result = (await router("initialize", { protocolVersion: "2025-03-26" })) as {
      protocolVersion: string;
      capabilities: Record<string, unknown>;
      serverInfo: { name: string; version: string };
    };
    expect(result.protocolVersion).toBe("2025-03-26");
    expect(result.serverInfo).toEqual({ name: "agentmemory", version: "9.9.9" });
    expect(result.capabilities).toHaveProperty("tools");
    expect(result.capabilities).toHaveProperty("resources");
    expect(result.capabilities).toHaveProperty("prompts");
  });

  it("initialize falls back to the server's protocolVersion when the client omits one", async () => {
    const router = createMcpMethodRouter(deps());
    const result = (await router("initialize", {})) as { protocolVersion: string };
    expect(result.protocolVersion).toBe("2024-11-05");
  });

  it("ping returns an empty object", async () => {
    const router = createMcpMethodRouter(deps());
    expect(await router("ping", {})).toEqual({});
  });

  it("notifications/initialized returns an empty object", async () => {
    const router = createMcpMethodRouter(deps());
    expect(await router("notifications/initialized", {})).toEqual({});
  });

  it("tools/list delegates to listTools", async () => {
    const d = deps();
    const router = createMcpMethodRouter(d);
    expect(await router("tools/list", {})).toEqual({ tools: [{ name: "memory_save" }] });
    expect(d.listTools).toHaveBeenCalledOnce();
  });

  it("tools/call passes name and arguments through to callTool", async () => {
    const d = deps();
    const router = createMcpMethodRouter(d);
    const result = await router("tools/call", {
      name: "memory_save",
      arguments: { content: "hi" },
    });
    expect(result).toEqual({ content: [{ type: "text", text: "ran memory_save" }] });
    expect(d.callTool).toHaveBeenCalledWith("memory_save", { content: "hi" });
  });

  it("tools/call defaults arguments to an empty object when omitted", async () => {
    const d = deps();
    const router = createMcpMethodRouter(d);
    await router("tools/call", { name: "memory_export" });
    expect(d.callTool).toHaveBeenCalledWith("memory_export", {});
  });

  it("tools/call without a name throws an Invalid params RpcError (-32602)", async () => {
    const router = createMcpMethodRouter(deps());
    await expect(router("tools/call", {})).rejects.toMatchObject({
      code: -32602,
    });
  });

  it("resources/read passes the uri through to readResource", async () => {
    const d = deps();
    const router = createMcpMethodRouter(d);
    const result = await router("resources/read", { uri: "agentmemory://status" });
    expect(result).toEqual({ contents: [{ uri: "agentmemory://status", text: "x" }] });
    expect(d.readResource).toHaveBeenCalledWith("agentmemory://status");
  });

  it("resources/read without a uri throws an Invalid params RpcError (-32602)", async () => {
    const router = createMcpMethodRouter(deps());
    await expect(router("resources/read", {})).rejects.toMatchObject({ code: -32602 });
  });

  it("prompts/get passes name and arguments through to getPrompt", async () => {
    const d = deps();
    const router = createMcpMethodRouter(d);
    await router("prompts/get", { name: "recall_context", arguments: { task_description: "t" } });
    expect(d.getPrompt).toHaveBeenCalledWith("recall_context", { task_description: "t" });
  });

  it("an unknown method throws a Method not found RpcError (-32601)", async () => {
    const router = createMcpMethodRouter(deps());
    const err = await router("does/not/exist", {}).catch((e) => e);
    expect(err).toBeInstanceOf(RpcError);
    expect((err as RpcError).code).toBe(-32601);
  });
});
