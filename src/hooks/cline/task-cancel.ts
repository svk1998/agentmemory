#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, sessionIdOf,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  ctx.postDetached("/observe", observePayload(input, "task_cancel", {}), 3000);
  await ctx.post("/session/end", { sessionId: sessionIdOf(input) }, 2500);
  return { cancel: false, contextModification: "", errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
  finishDetached();
}

main().catch(() => emit());
