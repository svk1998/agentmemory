#!/usr/bin/env bash
# Manual control for the local containerized agentmemory deployment.
#
#   ./deploy/local/agentmemory.sh start     # engine + worker up, wait for ready
#   ./deploy/local/agentmemory.sh stop      # both down
#   ./deploy/local/agentmemory.sh restart   # down then up
#   ./deploy/local/agentmemory.sh status    # container + livez status
#   ./deploy/local/agentmemory.sh logs      # follow worker logs
#   ./deploy/local/agentmemory.sh rebuild   # rebuild worker image after code changes
#
# The containers also carry restart: unless-stopped, so they return on their
# own when the Docker daemon starts. This script is for explicit control.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENGINE="$REPO_ROOT/docker-compose.yml"
WORKER="$REPO_ROOT/deploy/local/docker-compose.yml"
LIVEZ="http://localhost:3111/agentmemory/livez"

# The compose mount uses ${USERPROFILE} (set on Windows). On macOS/Linux fall
# back to $HOME so the ~/.agentmemory mount resolves there too.
export USERPROFILE="${USERPROFILE:-$HOME}"

wait_ready() {
  echo "Waiting for REST API at $LIVEZ ..."
  for _ in $(seq 1 30); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "$LIVEZ" 2>/dev/null)" = "200" ]; then
      echo "agentmemory is up -> http://localhost:3111  (MCP: /agentmemory/mcp)"
      return 0
    fi
    sleep 2
  done
  echo "REST API not ready within 60s. Check: ./deploy/local/agentmemory.sh logs"
}

start() {
  docker compose -f "$ENGINE" up -d
  docker compose -f "$WORKER" up -d
  wait_ready
}

stop() {
  docker compose -f "$WORKER" down
  docker compose -f "$ENGINE" down
  echo "agentmemory stopped."
}

status() {
  docker ps --filter name=agentmemory --filter name=iii-engine \
    --format '{{.Names}}: {{.Status}}'
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "$LIVEZ" 2>/dev/null || true)" = "200" ]; then
    echo "livez: 200 OK"
  else
    echo "livez: DOWN"
  fi
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    docker compose -f "$WORKER" logs -f ;;
  rebuild) docker compose -f "$WORKER" up -d --build; wait_ready ;;
  *)       echo "Usage: agentmemory.sh <start|stop|restart|status|logs|rebuild>" ;;
esac
