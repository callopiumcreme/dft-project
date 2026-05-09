#!/bin/bash
# PreToolUse hook: block rsync/ssh deploy to oistebio when git is dirty
# or HEAD diverges from origin/main.
#
# Stdin: JSON { tool_name: "Bash", tool_input: { command: "..." } }
# Exit 0 = allow. Exit 2 = block (stderr shown to Claude).

set -euo pipefail

REPO_ROOT="/mnt/c/Users/User/dft-project"

# Read stdin JSON
input="$(cat)"

# Extract command field; tolerate missing python/jq
cmd="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null || true)"

if [ -z "$cmd" ]; then
  exit 0
fi

# Match deploy-shaped commands targeting the demo server.
# - rsync ... oistebio:
# - ssh oistebio ... npm run build / pm2 restart dft-landing
case "$cmd" in
  *rsync*oistebio:*)
    is_deploy=1 ;;
  *"ssh oistebio"*"npm run build"*)
    is_deploy=1 ;;
  *"ssh oistebio"*"pm2 restart"*"dft-landing"*)
    is_deploy=1 ;;
  *)
    is_deploy=0 ;;
esac

if [ "$is_deploy" = "0" ]; then
  exit 0
fi

cd "$REPO_ROOT"

# 1) Working tree must be clean.
if [ -n "$(git status --porcelain)" ]; then
  echo "BLOCKED: deploy attempted with dirty working tree." >&2
  echo "Run: git status; commit + push first, then retry." >&2
  exit 2
fi

# 2) HEAD must equal origin/main (fetched copy is fine; we don't fetch here).
local_sha="$(git rev-parse HEAD)"
remote_sha="$(git rev-parse origin/main 2>/dev/null || echo 'unknown')"
if [ "$remote_sha" = "unknown" ]; then
  echo "BLOCKED: cannot resolve origin/main. Push at least once." >&2
  exit 2
fi
if [ "$local_sha" != "$remote_sha" ]; then
  echo "BLOCKED: HEAD ($local_sha) != origin/main ($remote_sha)." >&2
  echo "Push to origin/main before deploying so git matches the server." >&2
  exit 2
fi

exit 0
