#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout,
  sessionIdOf, cwdOf, contextString,
  type HookInput, type HookOutput, type Ctx,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx): Promise<HookOutput> {
  const cwd = cwdOf(input);
  const project = resolveProject(cwd);
  const sessionId = sessionIdOf(input);
  await ctx.post("/session/start", { sessionId, project, cwd }, 2000);
  const result = await ctx.post("/context", { sessionId, project }, 2500);
  return { cancel: false, contextModification: contextString(result), errorMessage: "" };
}

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig())));
}

main().catch(() => emit());
