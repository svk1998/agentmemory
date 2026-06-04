# Persistent local agentmemory WORKER, built from THIS repo so it includes the
# Streamable HTTP MCP endpoint (/agentmemory/mcp) and project-scoped recall.
# Connects to the iii-engine container; the engine serves REST on :3111 and
# routes to the functions this worker registers over the engine ws port.
FROM node:24-slim

# git: resolveProject() in the capture hooks/path logic shells out to
# `git rev-parse`. ca-certificates for outbound HTTPS (Groq, model downloads).
RUN apt-get update \
  && apt-get install -y --no-install-recommends git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install full deps (dev deps are needed for the tsdown build; optional deps
# provide the local embedding stack — onnxruntime-node etc. — with Linux
# prebuilts). package-lock is optional (the `*` keeps COPY happy if absent).
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Bring in the source and build dist/ (tsdown + the asset copies in the
# package.json build script, which work on Linux).
COPY . .
RUN npm run build

ENV NODE_ENV=production
# The engine owns the public :3111 socket; this worker only connects out to it
# and (optionally) serves the viewer on 3113 inside the container.
CMD ["node", "dist/index.mjs"]
