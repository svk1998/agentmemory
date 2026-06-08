#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, extractFilePaths, contextString,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const files = extractFilePaths(input.parameters);
  if (files.length === 0) {
    return { cancel: false, contextModification: "", errorMessage: "" };
  }
  const result = await ctx.post("/enrich", {
    sessionId: sessionIdOf(input),
    files: files.slice(0, 10),
    toolName: input.tool ?? "enrich_inject",
  }, 2500);
  return { cancel: false, contextModification: contextString(result), errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
