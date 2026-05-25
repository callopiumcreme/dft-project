#!/usr/bin/env bash
# Deploy orchestrator for the oistebio.usenexos.com host (Hetzner).
#
# Layout on the server (DO NOT change without updating this script):
#   /root/dft-project/backend   — synced from this repo, image rebuilt
#                                 via docker-compose.prod.yml override.
#   /root/dft-project/landing   — synced, built with `npm run build`,
#                                 served by pm2 process "dft-landing".
#   /root/dft-project/db        — Postgres data volume (NEVER touched
#                                 by this script).
#   /root/dft-project/.env*     — server-only secrets (NEVER overwritten).
#
# Usage:
#   scripts/deploy.sh                # backend + landing (default)
#   scripts/deploy.sh backend        # backend only
#   scripts/deploy.sh landing        # landing only
#   scripts/deploy.sh all            # explicit "all" alias
#   scripts/deploy.sh --dry-run all  # rsync -n + skip ssh side-effects
#   scripts/deploy.sh --skip-precheck backend
#                                    # bypass git-clean + branch check
#
# Safety: this script NEVER runs from CI or hooks; call it by hand.
# Project rule "Ask before deploy" (memory:feedback_deploy_discipline)
# still applies — the operator is responsible for batching pending work.
set -euo pipefail

REMOTE="oistebio"                                  # ~/.ssh/config alias
REMOTE_ROOT="/root/dft-project"
PM2_APP="dft-landing"
BACKEND_CONTAINER="dft-project-backend-1"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
DRY_RUN=0
SKIP_PRECHECK=0
TARGET="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=1; shift ;;
    --skip-precheck)  SKIP_PRECHECK=1; shift ;;
    -h|--help)
      sed -n '2,25p' "$0"
      exit 0
      ;;
    backend|landing|all) TARGET="$1"; shift ;;
    *) echo "deploy.sh: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mxx %s\033[0m\n' "$*" >&2; exit 1; }
maybe_ssh() {
  if (( DRY_RUN )); then
    printf '\033[2m[dry-run] ssh %s %q\033[0m\n' "$REMOTE" "$*"
  else
    ssh "$REMOTE" "$@"
  fi
}

# -----------------------------------------------------------------------------
# Pre-flight
# -----------------------------------------------------------------------------
if (( ! SKIP_PRECHECK )); then
  say "Pre-flight checks"
  branch=$(git rev-parse --abbrev-ref HEAD)
  [[ "$branch" == "main" ]] || die "Not on main (current: $branch). Use --skip-precheck to override."

  if [[ -n "$(git status --porcelain)" ]]; then
    die "Working tree dirty. Commit/stash first, or pass --skip-precheck."
  fi

  ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
  if [[ "$ahead" != "0" ]]; then
    die "$ahead local commit(s) not pushed to origin/main. Push first."
  fi
  echo "branch=main, tree clean, in sync with origin"
fi

# Remote sanity — fail fast if SSH or paths broken.
say "Remote sanity"
maybe_ssh "test -d $REMOTE_ROOT/backend && test -d $REMOTE_ROOT/landing && echo ok" \
  | grep -q ok || die "Remote paths missing under $REMOTE_ROOT on $REMOTE"

# -----------------------------------------------------------------------------
# Backend
# -----------------------------------------------------------------------------
deploy_backend() {
  say "Backend → rsync"
  local rflags=(-avz --delete)
  (( DRY_RUN )) && rflags+=(-n)

  rsync "${rflags[@]}" \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    --exclude='.env' --exclude='.env.*' \
    --exclude='tests/' \
    --exclude='*.xlsx' --exclude='*.sqlite' \
    backend/ "$REMOTE:$REMOTE_ROOT/backend/"

  say "Backend → docker build"
  maybe_ssh "cd $REMOTE_ROOT && docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend"

  say "Backend → up -d (recreate)"
  maybe_ssh "cd $REMOTE_ROOT && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend"

  # Container needs a moment to bind 8000 before alembic can connect.
  (( DRY_RUN )) || sleep 4

  say "Backend → alembic upgrade head"
  maybe_ssh "docker exec $BACKEND_CONTAINER alembic upgrade head"

  say "Backend → health probe"
  if (( ! DRY_RUN )); then
    code=$(ssh "$REMOTE" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health" || echo 000)
    [[ "$code" == "200" ]] || die "Backend /health returned $code"
    echo "health=200"
  fi
}

# -----------------------------------------------------------------------------
# Landing
# -----------------------------------------------------------------------------
deploy_landing() {
  say "Landing → rsync"
  local rflags=(-avz --delete)
  (( DRY_RUN )) && rflags+=(-n)

  # NEVER pass --delete-excluded — memory:feedback_rsync_env_files wipes
  # the server-only .env.local that the build needs at boot.
  rsync "${rflags[@]}" \
    --exclude='node_modules' --exclude='.next' --exclude='.git' \
    --exclude='.env' --exclude='.env.local' --exclude='.env.*' \
    --exclude='*.log' \
    landing/ "$REMOTE:$REMOTE_ROOT/landing/"

  say "Landing → npm run build"
  maybe_ssh "cd $REMOTE_ROOT/landing && npm run build"

  say "Landing → pm2 restart"
  maybe_ssh "pm2 restart $PM2_APP --update-env"

  say "Landing → public probe"
  if (( ! DRY_RUN )); then
    sleep 2
    code=$(curl -s -o /dev/null -w '%{http_code}' https://oistebio.usenexos.com/app/buyers || echo 000)
    # 307 = middleware redirect to /login (route reachable, JWT cookie absent).
    [[ "$code" == "307" || "$code" == "200" ]] || warn "Landing /app/buyers returned $code (expected 307)"
    echo "landing=$code"
  fi
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
case "$TARGET" in
  backend) deploy_backend ;;
  landing) deploy_landing ;;
  all)     deploy_backend; deploy_landing ;;
esac

say "Done."
