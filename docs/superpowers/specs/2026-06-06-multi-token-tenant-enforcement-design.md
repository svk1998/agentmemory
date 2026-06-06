# Design: Minimal multi-token + tenant enforcement

**Status:** Approved, deferred for future implementation
**Date:** 2026-06-06
**Author:** brainstormed with Claude Code

## Problem

agentmemory currently has a **flat, single-secret trust model**. Auth is one
shared bearer token: `src/mcp/server.ts:68` does a single
`timingSafeCompare(auth, "Bearer ${sec}")`, and the HMAC secret is generated
per-instance (`deploy/README.md:24`). Anyone holding it has full
read/write/**delete** across the entire store.

The `project` label (`resolveProject()` in `src/hooks/_project.ts`) is a soft
convenience scope derived from `AGENTMEMORY_PROJECT_NAME` → git toplevel → cwd
basename. Nothing *enforces* it — a caller can pass any project name and
read/write it. There is no identity, so `memory_audit` cannot attribute actions
to a person or team.

This blocks deploying a single instance to **multiple teams**: Team A can read,
overwrite, and `governance_delete` Team B's memories; you can't revoke one team
without rotating the secret for everyone; audit is unattributable.

The project roadmap acknowledges this — the entire Q4 2026 "Trust" theme (SSO
gateway, RBAC on memory scope, audit export; `ROADMAP.md:57-65`) is planned but
unshipped. This design is the **minimal slice** that unblocks safe multi-team
deployment without waiting for full OIDC/RBAC.

## Decisions (from brainstorming)

| Question | Decision |
|----------|----------|
| Isolation model | **Tenant + shared scopes** — each token has a home tenant plus optional grants on other tenants' projects |
| Token store | **Static config file** (plaintext, `chmod 600`); no issuance API, no DB |
| Back-compat | **Legacy secret = admin token** — no token file ⇒ today's behavior; file present ⇒ legacy secret is all-tenant superuser |
| Tenant ↔ project | **Tenant owns many projects** — tenant is a new top-level namespace; each project belongs to one tenant; memories get a new `tenant` tag at write time |

## 1. Scope & threat model

**In scope:** the **MCP surface** (`/agentmemory/mcp*`) — the documented path
teams connect through (`deploy/README.md`, Cline wiring). Scoped tokens
authenticate here; the data layer enforces tenant isolation on reads/writes.

**Deliberately out of scope (admin-only):** the raw REST API, `mem::mesh-*`
sync, and the viewer. These remain gated behind the **legacy single secret =
admin**. Teams are *never* given the admin secret — only scoped MCP tokens.
This is the key simplification keeping it "minimal": one new trust boundary
(MCP) rather than retrofitting identity across every HTTP trigger. The
roadmap's SSO gateway (Q4) eventually covers REST.

> **Implication / accepted risk:** tenant isolation holds *as long as the admin
> secret stays with operators*. If a team obtains the admin secret, isolation is
> void. Accepted for the minimal version. **Re-confirm at implementation time.**

## 2. Token file

Path `/data/tokens.json` (override via `AGENTMEMORY_TOKENS_FILE`), `chmod 600`,
same posture as the existing `.hmac`. Plaintext tokens.

```json
{
  "tokens": {
    "tok_acme_ci_9f3a...": {
      "tenant": "acme",
      "grants": [
        { "tenant": "globex", "project": "shared-types", "access": "read" }
      ]
    }
  }
}
```

- **Home tenant** → full read/write to all memories tagged `tenant=acme`.
- **Grants** → extra access to *another tenant's specific project*, identified by
  `(tenant, project)`, `access ∈ "read" | "write"`.
- **Delete / `governance_delete`** → home tenant or admin only (never via a
  grant) — safest default.
- Loaded at boot, cached in memory; `SIGHUP` (or a small `mtime` re-check)
  reloads without restart.
- Malformed file → **fail closed**: refuse to start, log which token entry is
  invalid.

**Future hardening (not in minimal):** store SHA-256 hashes of tokens instead of
plaintext so the at-rest file never contains usable credentials.

## 3. Data model

Add `tenant?: string` to the `Memory` interface (`src/types.ts:104`, alongside
`project`). That is the only schema change. Sessions/observations inherit tenant
from the writing principal, but the enforcement anchor is the `Memory` record —
matching how `src/functions/search.ts` already resolves project per-memory via
`loadMemoryProject` (`search.ts:387`).

## 4. Principal resolution (auth layer, `server.ts`)

Upgrade `checkAuth` (`server.ts:61`) from returning `McpResponse | null` to
returning a **`Principal` | 401**:

```
Bearer matches admin secret   → { admin: true }
Bearer found in token file     → { tenant, grants, admin: false }
No token file present          → { admin: true }   // back-compat: today's behavior
Otherwise                       → 401 unauthorized
```

```ts
interface Grant { tenant: string; project: string; access: "read" | "write"; }
interface Principal {
  admin: boolean;
  tenant?: string;     // undefined only when admin
  grants?: Grant[];
}
```

The `Principal` is resolved once in `mcp::tools::call` (`server.ts:99`) and
threaded into the `mem::*` payloads as a **server-trusted** field (e.g.
`__principal`). Clients cannot set it — the layer overwrites any client-supplied
value before dispatch.

## 5. Enforcement (data layer)

A shared helper centralizes every decision so call sites stay one-liners and the
logic is unit-testable in isolation:

```ts
function authorize(
  p: Principal,
  action: "read" | "write" | "delete",
  target: { tenant?: string; project?: string },
): boolean
```

Rules:
- `admin` → allow all.
- `read`: `target.tenant === p.tenant` OR `(target.tenant, target.project)`
  matches a grant (read or write).
- `write`: `target.tenant === p.tenant` OR matches a grant with `access:write`.
- `delete`: `target.tenant === p.tenant` only.
- Untagged target (`tenant === undefined`): admin only (see §6).

Two touch points:

- **Write** (`mem::remember`, `mem::observe`, `src/functions/actions.ts`): stamp
  `tenant = p.tenant` on the new `Memory`. A write targeting a *granted* foreign
  project is allowed only with `access:write`; otherwise the write is forced into
  the home tenant.
- **Read** (`mem::search` and recall-family): extend the existing post-fetch
  filter (`search.ts:368`) — a result is visible iff `authorize(p, "read",
  {tenant, project})`. Reuse the per-memory cache pattern by adding a parallel
  `loadMemoryTenant` next to `loadMemoryProject`.

## 6. Migration of existing data

Existing memories have `tenant === undefined`.

**Rule: untagged ⇒ visible to admin only.** No data destroyed, nothing leaks to
a scoped token. Safe-by-default. **Re-confirm at implementation time** whether
existing data should instead default to a named tenant.

An operator opt-in CLI backfills tenant on existing records when ready:

```
agentmemory tenant:assign --project <name> --tenant <name>
```

## 7. Error behavior

- Bad/absent token when a file exists → `401 unauthorized` (shape unchanged).
- Authenticated cross-tenant **read** → result filtered out silently (no leak
  via error — caller does not learn the memory exists).
- Cross-tenant **write/delete** → `403 forbidden` (new), so misconfig fails
  loud.

## 8. Testing

- `authorize()` unit table: home / grant / admin / untagged × read / write /
  delete.
- Token-file loader: valid, malformed (fail-closed), missing (back-compat
  admin), reload-on-change.
- Integration: two tokens on one instance — A cannot recall/forget B's memory;
  A *can* read B's granted project; a write stamps the correct tenant.
- Back-compat regression: no token file ⇒ existing single-secret behavior is
  byte-for-byte identical.

## Surface of the change

~1 schema field (`Memory.tenant`), 1 config file (`tokens.json`), 1 token-file
loader, 1 `authorize()` helper, an upgrade to `checkAuth`, and filter/stamp
calls at the read/write touch points. No new endpoints, no database, no breakage
for current single-secret installs.

## Open items to re-confirm before implementation

1. MCP-only enforcement boundary (admin secret stays with operators) —
   acceptable, or extend enforcement to the REST surface in this pass?
2. Untagged-existing-data ⇒ admin-only with opt-in backfill — agree, or default
   existing data to a named tenant?
