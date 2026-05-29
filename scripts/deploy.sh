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
#   scripts/deploy.sh                # compose + backend + data + landing
#   scripts/deploy.sh backend        # compose + backend + data
#   scripts/deploy.sh landing        # landing only
#   scripts/deploy.sh compose        # docker-compose*.yml → prod only
#   scripts/deploy.sh data           # data/ PDF dirs → prod only (additive)
#   scripts/deploy.sh all            # explicit "all" alias
#   scripts/deploy.sh --dry-run all  # rsync -n + skip ssh side-effects
#   scripts/deploy.sh --skip-precheck backend
#                                    # bypass git-clean + branch check
#
# Compose + data sync:
#   - docker-compose.yml + docker-compose.prod.yml are rsynced to prod so
#     mount/env edits actually reach the server. The next `docker compose
#     up -d backend` picks them up automatically (no force-recreate needed).
#   - data/ PDF dirs (customs, invoices, bl_ocean, certificates,
#     pos_documents, delivery_uk, transload) are rsynced WITHOUT --delete
#     — prod-only files are preserved (operator uploads, server-only doc
#     receipts). Safest setting; nothing is removed from prod by the script.
#
# Safety: this script NEVER runs from CI or hooks; call it by hand.
# Project rule "Ask before deploy" (memory:feedback_deploy_discipline)
# still applies — the operator is responsible for batching pending work.
set -euo pipefail

REMOTE="oistebio"                                  # ~/.ssh/config alias
REMOTE_ROOT="/root/dft-project"
PM2_APP="dft-landing"
BACKEND_CONTAINER="dft-project-backend-1"
DB_CONTAINER="dft-project-db-1"

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
    backend|landing|compose|data|all) TARGET="$1"; shift ;;
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
# Compose + data (additive)
# -----------------------------------------------------------------------------

# PDF dirs that the backend bind-mounts read-only. Anything else under
# data/ (sqlite, xlsx, ad-hoc dumps) is intentionally NOT synced.
DATA_DIRS=(
  data/customs
  data/invoices
  data/bl_ocean
  data/certificates
  data/pos_documents
  data/delivery_uk
  data/transload
)

deploy_compose() {
  say "Compose → rsync (docker-compose.yml + prod override)"
  local rflags=(-avz)
  (( DRY_RUN )) && rflags+=(-n)

  local files=(docker-compose.yml)
  [[ -f docker-compose.prod.yml ]] && files+=(docker-compose.prod.yml)

  rsync "${rflags[@]}" "${files[@]}" "$REMOTE:$REMOTE_ROOT/"
}

deploy_data() {
  say "Data dirs → rsync (additive, no --delete)"
  local rflags=(-avz)
  (( DRY_RUN )) && rflags+=(-n)

  local d
  for d in "${DATA_DIRS[@]}"; do
    if [[ ! -d "$d" ]]; then
      warn "Local $d missing — skipping"
      continue
    fi
    # Ensure target dir exists so the bind-mount has something to bind.
    # mkdir is idempotent; safe under --dry-run because we still need the
    # rsync output to be meaningful.
    (( DRY_RUN )) || ssh "$REMOTE" "mkdir -p $REMOTE_ROOT/$d"
    rsync "${rflags[@]}" \
      --exclude='*.xlsx' --exclude='*.sqlite' --exclude='.DS_Store' \
      --exclude='__pycache__' \
      "$d/" "$REMOTE:$REMOTE_ROOT/$d/"
  done
}

# -----------------------------------------------------------------------------
# Backend
# -----------------------------------------------------------------------------

# Fingerprint of active mass_balance_ledger state on prod.
# Format: "<row_count>:<sum_kg_in>:<sum_kg_out>".
# Used to catch a deploy step (migration or manual command) that silently
# writes phantom rows to the ledger. The cleanup from 2026-05-27 inserted
# 2338 phantom rows on prod that local didn't have; the next deploy should
# never repeat that — capture before alembic, capture after, diff.
ledger_fingerprint() {
  ssh "$REMOTE" "docker exec $DB_CONTAINER psql -U dft -d dft -tAc \"SELECT COUNT(*) || ':' || COALESCE(SUM(kg_in),0)::text || ':' || COALESCE(SUM(kg_out),0)::text FROM mass_balance_ledger WHERE deleted_at IS NULL;\"" 2>/dev/null | tr -d '[:space:]'
}

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

  # Snapshot the mass_balance_ledger fingerprint BEFORE the new backend
  # container comes up so we can detect any phantom writes introduced by
  # alembic migrations or by manual commands that piggyback the deploy.
  local ledger_pre=""
  if (( ! DRY_RUN )); then
    say "Backend → ledger fingerprint (pre)"
    ledger_pre="$(ledger_fingerprint)"
    echo "ledger_pre=$ledger_pre"
  fi

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

  # Refuse to call the deploy done if the migration step silently mutated
  # the mass_balance_ledger. New rows must come from explicit ingest paths,
  # never from a deploy-time backfill.
  if (( ! DRY_RUN )); then
    say "Backend → ledger fingerprint (post)"
    local ledger_post
    ledger_post="$(ledger_fingerprint)"
    echo "ledger_post=$ledger_post"
    if [[ "$ledger_pre" != "$ledger_post" ]]; then
      warn "mass_balance_ledger fingerprint changed during alembic upgrade!"
      warn "  pre  = $ledger_pre"
      warn "  post = $ledger_post"
      die "Phantom ledger writes detected — inspect prod before considering deploy successful (memory:feedback_deploy_no_runtime_backfill)."
    fi
    echo "ledger unchanged ✓"
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
  backend) deploy_compose; deploy_backend; deploy_data ;;
  landing) deploy_landing ;;
  compose) deploy_compose ;;
  data)    deploy_data ;;
  all)     deploy_compose; deploy_backend; deploy_data; deploy_landing ;;
esac

say "Done."
