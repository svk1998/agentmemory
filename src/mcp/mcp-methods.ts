import { RpcError, type RequestHandler } from "./transport.js";

export interface McpServerInfo {
  name: string;
  version: string;
  protocolVersion: string;
}

// Transport-neutral handler callbacks. Each returns the MCP `result` payload
// for its method (e.g. `{ tools }`, `{ content }`, `{ contents }`,
// `{ messages }`). The router owns JSON-RPC method routing and argument
// validation; the callbacks own the actual work, so the same router serves
// both stdio and HTTP transports.
export interface McpMethodDeps {
  serverInfo: McpServerInfo;
  listTools: () => Promise<unknown> | unknown;
  callTool: (
    name: string,
    args: Record<string, unknown>,
  ) => Promise<unknown> | unknown;
  listResources: () => Promise<unknown> | unknown;
  readResource: (uri: string) => Promise<unknown> | unknown;
  listPrompts: () => Promise<unknown> | unknown;
  getPrompt: (
    name: string,
    args: Record<string, string>,
  ) => Promise<unknown> | unknown;
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new RpcError(-32602, `Invalid params: ${field} is required`);
  }
  return value;
}

/**
 * Builds a {@link RequestHandler} that routes MCP JSON-RPC methods to the
 * injected callbacks. The handler is transport-agnostic: pair it with the
 * stdio transport's `processLine` / `dispatchMessage`, or call it from an
 * HTTP endpoint.
 */
export function createMcpMethodRouter(deps: McpMethodDeps): RequestHandler {
  return async (method, params) => {
    switch (method) {
      case "initialize": {
        const requested = params["protocolVersion"];
        return {
          protocolVersion:
            typeof requested === "string" && requested.trim()
              ? requested
              : deps.serverInfo.protocolVersion,
          capabilities: {
            tools: { listChanged: false },
            resources: { listChanged: false },
            prompts: { listChanged: false },
          },
          serverInfo: {
            name: deps.serverInfo.name,
            version: deps.serverInfo.version,
          },
        };
      }

      // Notifications carry no id, so dispatchMessage drops whatever we
      // return here — but returning {} keeps the handler total.
      case "notifications/initialized":
      case "notifications/cancelled":
      case "ping":
        return {};

      case "tools/list":
        return deps.listTools();

      case "tools/call": {
        const name = requireString(params["name"], "name");
        const args =
          (params["arguments"] as Record<string, unknown> | undefined) || {};
        return deps.callTool(name, args);
      }

      case "resources/list":
        return deps.listResources();

      case "resources/read": {
        const uri = requireString(params["uri"], "uri");
        return deps.readResource(uri);
      }

      case "prompts/list":
        return deps.listPrompts();

      case "prompts/get": {
        const name = requireString(params["name"], "name");
        const args =
          (params["arguments"] as Record<string, string> | undefined) || {};
        return deps.getPrompt(name, args);
      }

      default:
        throw new RpcError(-32601, `Method not found: ${method}`);
    }
  };
}
