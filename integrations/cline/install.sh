#!/usr/bin/env bash
set -euo pipefail

PROJECT=""
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --project=*) PROJECT="${arg#*=}" ;;
    --uninstall) UNINSTALL=1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPTS_SRC="$REPO_ROOT/plugin/cline/scripts"

if [ -n "$PROJECT" ]; then
  HOOKS_DIR="$(cd "$PROJECT" && pwd)/.clinerules/hooks"
else
  HOOKS_DIR="$HOME/Documents/Cline/Rules/Hooks"
fi
AGENT_DIR="$HOOKS_DIR/.agentmemory"

# Hook type -> compiled script. Keep in sync with src/cli/connect/cline-hooks.ts.
HOOKS="TaskStart:task-start.mjs TaskResume:task-resume.mjs TaskCancel:task-cancel.mjs \
TaskComplete:task-complete.mjs PreToolUse:pre-tool-use.mjs PostToolUse:post-tool-use.mjs \
UserPromptSubmit:prompt-submit.mjs PreCompact:pre-compact.mjs"

if [ "$UNINSTALL" -eq 1 ]; then
  for pair in $HOOKS; do rm -f "$HOOKS_DIR/${pair%%:*}"; done
  rm -rf "$AGENT_DIR"
  echo "Uninstalled agentmemory Cline hooks from $HOOKS_DIR"
  exit 0
fi

[ -d "$SCRIPTS_SRC" ] || { echo "Compiled scripts not found at $SCRIPTS_SRC. Run 'npx tsdown' first." >&2; exit 1; }

mkdir -p "$AGENT_DIR"
cp "$SCRIPTS_SRC"/*.mjs "$AGENT_DIR"/

URL="${AGENTMEMORY_URL:-http://localhost:3111}"
SECRET="${AGENTMEMORY_SECRET:-}"
DOTENV="$HOME/.agentmemory/.env"
if [ -z "$SECRET" ] && [ -f "$DOTENV" ]; then
  SECRET="$(grep -E '^\s*AGENTMEMORY_SECRET\s*=' "$DOTENV" | head -n1 | sed -E 's/^\s*AGENTMEMORY_SECRET\s*=\s*//' | tr -d '"'"'"' )"
fi
printf '{"url":"%s","secret":"%s"}' "$URL" "$SECRET" > "$AGENT_DIR/config.json"
chmod 600 "$AGENT_DIR/config.json"

for pair in $HOOKS; do
  name="${pair%%:*}"; script="${pair#*:}"
  cat > "$HOOKS_DIR/$name" <<EOF
#!/usr/bin/env bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec node "\$DIR/.agentmemory/$script"
EOF
  chmod +x "$HOOKS_DIR/$name"
done

echo "Installed agentmemory Cline hooks to $HOOKS_DIR"
[ -n "$SECRET" ] && echo "Auth: Bearer secret configured" || echo "Auth: no secret (open local deployment)"
