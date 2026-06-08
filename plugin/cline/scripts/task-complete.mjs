#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
//#region src/hooks/cline/_cline.ts
const DEFAULT_URL = "http://localhost:3111";
function authHeaders(secret) {
	const h = { "Content-Type": "application/json" };
	if (secret) h["Authorization"] = `Bearer ${secret}`;
	return h;
}
function resolveConfig(configDir) {
	let url = process.env["AGENTMEMORY_URL"] || "";
	let secret = process.env["AGENTMEMORY_SECRET"] || "";
	if (!url || !secret) try {
		const raw = readFileSync(join(configDir, "config.json"), "utf-8");
		const file = JSON.parse(raw);
		if (!url && typeof file.url === "string") url = file.url;
		if (!secret && typeof file.secret === "string") secret = file.secret;
	} catch {}
	return {
		url: url || DEFAULT_URL,
		secret
	};
}
function loadConfig() {
	return resolveConfig(dirname(fileURLToPath(import.meta.url)));
}
function sessionIdOf(input) {
	return input.taskId || `cline_${Date.now().toString(36)}`;
}
function buildOutput(partial) {
	return {
		cancel: false,
		contextModification: partial.contextModification ?? "",
		errorMessage: partial.errorMessage ?? ""
	};
}
async function readInput() {
	let raw = "";
	for await (const chunk of process.stdin) raw += chunk;
	try {
		return JSON.parse(raw);
	} catch {
		return null;
	}
}
let emitted = false;
function emit(partial = {}) {
	if (emitted) return;
	emitted = true;
	process.stdout.write(JSON.stringify(buildOutput(partial)));
}
function registerHardTimeout(ms = 5e3) {
	setTimeout(() => {
		emit();
		process.exit(0);
	}, ms).unref();
}
function finishDetached(ms = 600) {
	setTimeout(() => process.exit(0), ms).unref();
}
async function post(cfg, path, body, timeoutMs) {
	try {
		const res = await fetch(`${cfg.url}/agentmemory${path}`, {
			method: "POST",
			headers: authHeaders(cfg.secret),
			body: JSON.stringify(body),
			signal: AbortSignal.timeout(timeoutMs)
		});
		if (!res.ok) return null;
		return await res.json().catch(() => null);
	} catch {
		return null;
	}
}
function postDetached(cfg, path, body, timeoutMs) {
	fetch(`${cfg.url}/agentmemory${path}`, {
		method: "POST",
		headers: authHeaders(cfg.secret),
		body: JSON.stringify(body),
		signal: AbortSignal.timeout(timeoutMs)
	}).catch(() => {});
}
function makeCtx(cfg) {
	return {
		cfg,
		post: (p, b, t) => post(cfg, p, b, t),
		postDetached: (p, b, t) => postDetached(cfg, p, b, t)
	};
}
//#endregion
//#region src/hooks/cline/task-complete.ts
async function run(input, ctx) {
	const sessionId = sessionIdOf(input);
	await ctx.post("/summarize", { sessionId }, 2500);
	await ctx.post("/session/end", { sessionId }, 2500);
	ctx.postDetached("/consolidate-pipeline", {
		tier: "all",
		force: true
	}, 3e4);
	ctx.postDetached("/crystals/auto", { olderThanDays: 7 }, 3e4);
	return {
		cancel: false,
		contextModification: "",
		errorMessage: ""
	};
}
async function main() {
	registerHardTimeout();
	const input = await readInput();
	if (!input) return emit();
	emit(await run(input, makeCtx(loadConfig())));
	finishDetached(800);
}
main().catch(() => emit());
//#endregion
export { run };

//# sourceMappingURL=task-complete.mjs.map