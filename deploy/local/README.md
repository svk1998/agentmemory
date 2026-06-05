# Local containerized deployment

Run agentmemory as an always-on local service: the **iii-engine** container
(from the repo-root `docker-compose.yml`) plus a **worker** container built
from *this* repo (so it includes the Streamable HTTP MCP endpoint and
project-scoped recall). Both carry `restart: unless-stopped`, so the stack
comes back on its own once the Docker daemon starts.

State (memories, BM25/vector index, graph) lives in the engine's `iii-data`
volume — the worker is stateless and safe to rebuild.

## Prerequisites

- Docker (Docker Desktop on Windows/macOS, native Docker Engine on Linux).
- The engine container running (repo-root `docker-compose.yml`).

## Quick start

```bash
# Windows (PowerShell)
.\deploy\local\agentmemory.ps1 start

# macOS / Linux / git-bash
./deploy/local/agentmemory.sh start
```

Both wrap the engine + worker composes and wait for `GET /agentmemory/livez`.
Other verbs: `stop`, `restart`, `status`, `logs`, `rebuild` (rebuild after
changing source).

To bring it up by hand:

```bash
docker compose -f docker-compose.yml up -d                      # engine
docker compose -f deploy/local/docker-compose.yml up -d --build # worker (+ viewer forwarder)
```

## Provider keys (optional)

Put keys in `~/.agentmemory/.env` (mounted into the worker; kept out of the
image/compose). It works with zero keys (BM25-only, synthetic compression).
Example using Groq via the OpenAI-compatible path:

```bash
OPENAI_API_KEY=<groq-key>
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
GRAPH_EXTRACTION_ENABLED=true
CONSOLIDATION_ENABLED=true
EMBEDDING_PROVIDER=local            # Groq has no embeddings endpoint; pin local
```

Restart the worker after editing: `agentmemory.{sh,ps1} restart`.

## Viewer

The worker serves the dashboard on the container's `127.0.0.1:3113`. A small
`socat` sidecar (`viewer-forward`) relays it to host loopback, so
`http://localhost:3113` works **on this machine only** (not the LAN). The
viewer's own code refuses a non-loopback bind without a secret — the relay
keeps it loopback while still reaching it.

## LAN access (reach the server from another machine)

By default the engine binds REST/MCP to `127.0.0.1:3111` (this machine only).
To expose it on the LAN:

1. **Set a bearer secret** (mandatory — an open read/write/delete API on the
   network is a non-starter). Add to `~/.agentmemory/.env`:
   ```bash
   AGENTMEMORY_SECRET=<32-byte-hex>     # e.g. `openssl rand -hex 32`
   ```
2. **Bind the port to all interfaces.** The root compose uses
   `${AGENTMEMORY_BIND:-127.0.0.1}:3111:3111`, so set it (gitignored repo
   `.env` is the easy spot):
   ```bash
   echo "AGENTMEMORY_BIND=0.0.0.0" >> .env
   ```
   Then recreate the engine: `docker compose -f docker-compose.yml up -d`.
3. **Open the firewall** for inbound TCP 3111:
   - Windows (admin PowerShell):
     ```powershell
     New-NetFirewallRule -DisplayName "agentmemory 3111 (LAN)" -Direction Inbound `
       -Action Allow -Protocol TCP -LocalPort 3111 -Profile Private
     ```
   - Linux: `sudo ufw allow 3111/tcp`
4. Restart the worker so it picks up the secret: `agentmemory.{sh,ps1} restart`.

Now `http://<host-LAN-IP>:3111/agentmemory/mcp` is reachable with the bearer.

> **Security:** traffic is plaintext HTTP — the bearer is sniffable on the
> network. Fine for a trusted LAN. For anything stronger use Tailscale or a
> TLS reverse proxy. A DHCP-assigned host IP can change; reserve a static IP.

## Connect MCP clients

Replace `<HOST>` with `localhost` (same machine) or the server's LAN IP, and
`<SECRET>` with `AGENTMEMORY_SECRET` (omit `headers` entirely if no secret).

### Claude Code

```bash
claude mcp add --transport http agentmemory \
  http://<HOST>:3111/agentmemory/mcp \
  --header "Authorization: Bearer <SECRET>"
```

### Cline (VS Code) — `cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "agentmemory": {
      "type": "streamableHttp",
      "url": "http://<HOST>:3111/agentmemory/mcp",
      "headers": { "Authorization": "Bearer <SECRET>" },
      "disabled": false,
      "autoApprove": ["memory_recall", "memory_smart_search", "memory_sessions",
                      "memory_file_history", "memory_timeline", "memory_profile",
                      "memory_graph_query"]
    }
  }
}
```

Cline settings file location:
- Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- macOS: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

Cline calls the transport `streamableHttp`; Claude Code calls it `http` — same
Streamable HTTP protocol, and both send the `headers` you configure.

## Linux notes

- **Native alternative (no Docker):** unlike Windows, the iii-engine binary
  auto-installs on Linux, so `npx @agentmemory/agentmemory` runs the whole
  stack natively. Pair with a `systemd` unit + `ufw allow 3111/tcp` for a
  clean always-on server — often the better home for a LAN server than a
  desktop.
- **Docker recipe on Linux:** use `agentmemory.sh` (it exports
  `USERPROFILE=$HOME` so the `~/.agentmemory` mount resolves). The compose
  mount is `${USERPROFILE:-$HOME}/.agentmemory`, so it also works if you run
  `docker compose` directly. The `.ps1` script is Windows-only.

## Capture hooks and the secret

If you enable `AGENTMEMORY_SECRET`, the host-side Claude Code capture hooks
must also send it — they read `AGENTMEMORY_SECRET` from the environment, so
set it as a user/system env var (Windows `setx`, Linux shell profile) and
restart Claude Code so hook subprocesses inherit it. Until then the hooks get
401 and capture pauses (no data loss; recall via the import path can backfill).
