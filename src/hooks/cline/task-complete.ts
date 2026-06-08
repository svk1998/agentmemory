#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  sessionIdOf,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const sessionId = sessionIdOf(input);
  await ctx.post("/summarize", { sessionId }, 2500);
  await ctx.post("/session/end", { sessionId }, 2500);
  // Heavy maintenance — fire-and-forget, generous timeout.
  ctx.postDetached("/consolidate-pipeline", { tier: "all", force: true }, 30000);
  ctx.postDetached("/crystals/auto", { olderThanDays: 7 }, 30000);
  return { cancel: false, contextModification: "", errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
  finishDetached(800);
}

main().catch(() => emit());
