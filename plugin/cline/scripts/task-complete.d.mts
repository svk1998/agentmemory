//#region src/hooks/cline/_cline.d.ts
interface HookInput {
  clineVersion?: string;
  hookName?: string;
  timestamp?: string;
  taskId?: string;
  workspaceRoots?: string[];
  userId?: string;
  tool?: string;
  parameters?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  durationMs?: number;
  prompt?: string;
  attachments?: unknown[];
  [k: string]: unknown;
}
interface HookOutput {
  cancel: boolean;
  contextModification: string;
  errorMessage: string;
}
interface Config {
  url: string;
  secret: string;
}
interface Ctx {
  cfg: Config;
  post(path: string, body: unknown, timeoutMs: number): Promise<Record<string, unknown> | null>;
  postDetached(path: string, body: unknown, timeoutMs: number): void;
}
//#endregion
//#region src/hooks/cline/task-complete.d.ts
declare function run(input: HookInput, ctx: Ctx): Promise<HookOutput>;
//#endregion
export { run };
//# sourceMappingURL=task-complete.d.mts.map