// Canonical mapping of Cline hook types → compiled script files, plus the
// per-platform shim text. Source of truth for integrations/cline/install.*.
// Keep this list in sync with clineHookEntries in tsdown.config.ts.
export interface ClineHook {
  hookName: string; // Cline discovers a file named exactly this (+ .ps1 on Windows)
  scriptFile: string; // compiled .mjs under .agentmemory/
}

export const CLINE_HOOKS: ClineHook[] = [
  { hookName: "TaskStart", scriptFile: "task-start.mjs" },
  { hookName: "TaskResume", scriptFile: "task-resume.mjs" },
  { hookName: "TaskCancel", scriptFile: "task-cancel.mjs" },
  { hookName: "TaskComplete", scriptFile: "task-complete.mjs" },
  { hookName: "PreToolUse", scriptFile: "pre-tool-use.mjs" },
  { hookName: "PostToolUse", scriptFile: "post-tool-use.mjs" },
  { hookName: "UserPromptSubmit", scriptFile: "prompt-submit.mjs" },
  { hookName: "PreCompact", scriptFile: "pre-compact.mjs" },
];

export function buildPwshShim(scriptFile: string): string {
  return [
    "$ErrorActionPreference = 'SilentlyContinue'",
    "$stdin = [Console]::In.ReadToEnd()",
    `$stdin | node "$PSScriptRoot\\.agentmemory\\${scriptFile}"`,
    "",
  ].join("\r\n");
}

export function buildPosixWrapper(scriptFile: string): string {
  return [
    "#!/usr/bin/env bash",
    'DIR="$(cd "$(dirname "$0")" && pwd)"',
    `exec node "$DIR/.agentmemory/${scriptFile}"`,
    "",
  ].join("\n");
}
