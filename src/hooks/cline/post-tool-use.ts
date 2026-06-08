#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, truncate,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const success = input.success !== false;
  ctx.postDetached("/observe", observePayload(
    input,
    success ? "post_tool_use" : "post_tool_failure",
    {
      tool_name: input.tool,
      tool_input: truncate(input.parameters, 4000),
      tool_output: truncate(input.result, 8000),
      duration_ms: typeof input.durationMs === "number" ? input.durationMs : null,
    },
  ), 3000);
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
