#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, cwdOf, contextString, CLINE_INSTRUCTIONS,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const cwd = cwdOf(input);
  const result = await ctx.post("/session/start", {
    sessionId: sessionIdOf(input),
    project: resolveProject(cwd),
    cwd,
  }, 2500);
  const ctxText = contextString(result);
  const injection = [CLINE_INSTRUCTIONS, ctxText].filter(Boolean).join("\n\n");
  return { cancel: false, contextModification: injection, errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
