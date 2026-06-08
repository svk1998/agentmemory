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
