import { describe, it, expect, vi } from "vitest";
import {
  dispatchMessage,
  RpcError,
  type RequestHandler,
} from "../src/mcp/transport.js";

const okHandler: RequestHandler = async (method) => ({ method });

describe("dispatchMessage — already-parsed JSON-RPC values", () => {
  it("returns a result response for a valid request with an id", async () => {
    const res = await dispatchMessage(
      { jsonrpc: "2.0", id: 1, method: "tools/list" },
      okHandler,
    );
    expect(res).toEqual({ jsonrpc: "2.0", id: 1, result: { method: "tools/list" } });
  });

  it("returns null for a notification (no id) even though the handler ran", async () => {
    const handler = vi.fn(okHandler);
    const res = await dispatchMessage(
      { jsonrpc: "2.0", method: "notifications/initialized" },
      handler,
    );
    expect(res).toBeNull();
    expect(handler).toHaveBeenCalledOnce();
  });

  it("returns null for a notification with id: null", async () => {
    const res = await dispatchMessage(
      { jsonrpc: "2.0", id: null, method: "notifications/cancelled" },
      okHandler,
    );
    expect(res).toBeNull();
  });

  it("maps a thrown RpcError to its own code", async () => {
    const handler: RequestHandler = async () => {
      throw new RpcError(-32601, "Method not found: x");
    };
    const res = await dispatchMessage(
      { jsonrpc: "2.0", id: 5, method: "x" },
      handler,
    );
    expect(res).toEqual({
      jsonrpc: "2.0",
      id: 5,
      error: { code: -32601, message: "Method not found: x" },
    });
  });

  it("maps a thrown plain Error to -32603 Internal error", async () => {
    const handler: RequestHandler = async () => {
      throw new Error("boom");
    };
    const res = await dispatchMessage(
      { jsonrpc: "2.0", id: 7, method: "tools/call" },
      handler,
    );
    expect(res?.id).toBe(7);
    expect(res?.error?.code).toBe(-32603);
    expect(res?.error?.message).toBe("boom");
  });

  it("logs but returns null when a notification handler throws", async () => {
    const errs: string[] = [];
    const handler: RequestHandler = async () => {
      throw new Error("notif crash");
    };
    const res = await dispatchMessage(
      { jsonrpc: "2.0", method: "notifications/initialized" },
      handler,
      (m) => errs.push(m),
    );
    expect(res).toBeNull();
    expect(errs.join("")).toContain("notif crash");
  });

  it("returns Invalid Request (-32600) echoing a string id when jsonrpc is missing", async () => {
    const res = await dispatchMessage({ id: "a", method: "tools/list" }, okHandler);
    expect(res).toEqual({
      jsonrpc: "2.0",
      id: "a",
      error: { code: -32600, message: "Invalid Request" },
    });
  });

  it("returns null for a malformed message with no id (treated as notification)", async () => {
    const res = await dispatchMessage({ method: "broken" }, okHandler);
    expect(res).toBeNull();
  });

  it("returns Invalid Request (-32600) with id: null when id is a non-primitive on a valid shape", async () => {
    const handler = vi.fn(okHandler);
    const res = await dispatchMessage(
      { jsonrpc: "2.0", id: { bogus: true }, method: "tools/list" },
      handler,
    );
    expect(res?.id).toBeNull();
    expect(res?.error?.code).toBe(-32600);
    expect(handler).not.toHaveBeenCalled();
  });
});
