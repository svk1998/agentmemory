#!/usr/bin/env node
import {
  readInput, loadConfig, makeCtx, emit, registerHardTimeout, finishDetached,
  observePayload, sessionIdOf, cwdOf, renderSearchResults,
  type HookInput, type HookOutput, type Ctx, type CompactResult,
} from "./_cline.js";
import { resolveProject } from "../_project.js";

export async function run(input: HookInput, ctx: Ctx, injectOnPrompt: boolean): Promise<HookOutput> {
  const prompt = typeof input.prompt === "string" ? input.prompt : "";
  ctx.postDetached("/observe", observePayload(input, "prompt_submit", {
    prompt: prompt.slice(0, 8000),
    attachments: Array.isArray(input.attachments) ? input.attachments.length : 0,
  }), 3000);

  if (!injectOnPrompt || !prompt) {
    return { cancel: false, contextModification: "", errorMessage: "" };
  }
  const result = await ctx.post("/smart-search", {
    query: prompt,
    sessionId: sessionIdOf(input),
    project: resolveProject(cwdOf(input)),
    limit: 8,
  }, 2500);
  const results = (result?.results as CompactResult[] | undefined) ?? [];
  return {
    cancel: false,
    contextModification: renderSearchResults(prompt, results),
    errorMessage: "",
  };
}

const INJECT = process.env["AGENTMEMORY_INJECT_ON_PROMPT"] === "true";

async function main() {
  registerHardTimeout();
  const input = await readInput();
  if (!input) return emit();
  emit(await run(input, makeCtx(loadConfig()), INJECT));
  if (!INJECT) finishDetached();
}

main().catch(() => emit());
