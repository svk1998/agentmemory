#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname, join } from "node:path";
import { execSync } from "node:child_process";
//#region src/hooks/_project.ts
function resolveProject(cwd) {
	const explicit = process.env["AGENTMEMORY_PROJECT_NAME"];
	if (explicit && explicit.trim()) return explicit.trim();
	const dir = cwd && cwd.trim() ? cwd : process.cwd();
	try {
		const top = execSync("git rev-parse --show-toplevel", {
			cwd: dir,
			stdio: [
				"ignore",
				"pipe",
				"ignore"
			],
			timeout: 500
		}).toString().trim();
		if (top) return basename(top);
	} catch {}
	return basename(dir);
}
//#endregion
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
function cwdOf(input) {
	const roots = input.workspaceRoots;
	if (Array.isArray(roots) && roots.length > 0 && typeof roots[0] === "string") return roots[0];
	return process.cwd();
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
function contextString(result) {
	return result && typeof result.context === "string" ? result.context : "";
}
//#endregion
//#region src/hooks/cline/pre-compact.ts
async function run(input, ctx) {
	const sessionId = sessionIdOf(input);
	const project = resolveProject(cwdOf(input));
	await ctx.post("/summarize", { sessionId }, 2500);
	return {
		cancel: false,
		contextModification: contextString(await ctx.post("/context", {
			sessionId,
			project
		}, 2500)),
		errorMessage: ""
	};
}
async function main() {
	registerHardTimeout();
	const input = await readInput();
	if (!input) return emit();
	emit(await run(input, makeCtx(loadConfig())));
}
main().catch(() => emit());
//#endregion
export { run };

//# sourceMappingURL=pre-compact.mjs.map