#!/usr/bin/env bash
#
# snapshot_db.sh — Cryptographic Postgres snapshot for RTFO-310125 audit trail.
#
# Story: E1-S1.16 / DFTEN-110
#
# Produces a gzip-compressed pg_dump of the DFT Postgres database plus a
# SHA-256 side-car, written under:
#   deliverables/RTFO-310125/05_audit_trail/db_snapshots/
#
# Intended use:
#   - Day 5 (preliminary) and Day 6 (FINAL) of the 5-working-day RTFO
#     submission window.
#   - Idempotent within a single UTC day: re-runs overwrite the day's archive
#     and emit a stderr warning.
#
# Exit codes:
#   0   success
#   >0  any failure (set -euo pipefail propagates)

set -euo pipefail

# ----- Locate repo root ------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ----- Resolve DB container name --------------------------------------------
# Prefer `docker compose ps` (compose v2); fall back to legacy `docker-compose`;
# fall back finally to the known default `dft-db` / `dft-project_db_1`.
detect_db_container() {
    local name=""

    if docker compose version >/dev/null 2>&1; then
        name="$(cd "${REPO_ROOT}" && docker compose ps -q db 2>/dev/null | head -n1 || true)"
        if [[ -n "${name}" ]]; then
            docker inspect --format '{{.Name}}' "${name}" 2>/dev/null | sed 's#^/##'
            return 0
        fi
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        name="$(cd "${REPO_ROOT}" && docker-compose ps -q db 2>/dev/null | head -n1 || true)"
        if [[ -n "${name}" ]]; then
            docker inspect --format '{{.Name}}' "${name}" 2>/dev/null | sed 's#^/##'
            return 0
        fi
    fi

    # Fallbacks: try known container names in priority order.
    for candidate in dft-db dft-project_db_1 dft_db_1; do
        if docker inspect "${candidate}" >/dev/null 2>&1; then
            echo "${candidate}"
            return 0
        fi
    done

    return 1
}

DB_CONTAINER="$(detect_db_container || true)"
if [[ -z "${DB_CONTAINER:-}" ]]; then
    echo "ERROR: could not locate Postgres container (tried compose service 'db' and fallbacks dft-db / dft-project_db_1 / dft_db_1)" >&2
    exit 1
fi

# ----- Resolve POSTGRES_USER / POSTGRES_DB ----------------------------------
# Source from .env if present; otherwise read from the running container env;
# finally fall back to sensible defaults.
PG_USER=""
PG_DB=""

if [[ -f "${REPO_ROOT}/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    # shellcheck source=/dev/null
    . "${REPO_ROOT}/.env"
    set +a
    PG_USER="${POSTGRES_USER:-}"
    PG_DB="${POSTGRES_DB:-}"
fi

if [[ -z "${PG_USER}" ]]; then
    PG_USER="$(docker exec "${DB_CONTAINER}" printenv POSTGRES_USER 2>/dev/null || true)"
fi
if [[ -z "${PG_DB}" ]]; then
    PG_DB="$(docker exec "${DB_CONTAINER}" printenv POSTGRES_DB 2>/dev/null || true)"
fi

PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-dft}"

# ----- Compute paths & timestamp --------------------------------------------
TS="$(date -u +%Y-%m-%d)"
OUTDIR="${REPO_ROOT}/deliverables/RTFO-310125/05_audit_trail/db_snapshots"
ARCHIVE="db_snapshot_${TS}.sql.gz"
HASHFILE="db_snapshot_${TS}.sha256"

mkdir -p "${OUTDIR}"

if [[ -f "${OUTDIR}/${ARCHIVE}" ]]; then
    echo "WARN: ${ARCHIVE} already exists in ${OUTDIR}; overwriting." >&2
fi

# ----- Dump -----------------------------------------------------------------
echo "Snapshotting Postgres database '${PG_DB}' as user '${PG_USER}' from container '${DB_CONTAINER}' ..." >&2

# pg_dump -> gzip pipeline. Pipefail (set -o pipefail above) ensures a failure
# in pg_dump bubbles up even though gzip succeeds.
docker exec -i "${DB_CONTAINER}" pg_dump -U "${PG_USER}" -d "${PG_DB}" \
    | gzip -9 > "${OUTDIR}/${ARCHIVE}"

# ----- Side-car SHA-256 -----------------------------------------------------
# Run inside OUTDIR so the hashfile records the filename only (no abs path).
(
    cd "${OUTDIR}"
    sha256sum "${ARCHIVE}" > "${HASHFILE}"
)

# ----- Report ---------------------------------------------------------------
SIZE_BYTES="$(stat -c '%s' "${OUTDIR}/${ARCHIVE}" 2>/dev/null || stat -f '%z' "${OUTDIR}/${ARCHIVE}")"
SIZE_HUMAN="$(du -h "${OUTDIR}/${ARCHIVE}" | awk '{print $1}')"
SHA="$(awk '{print $1}' "${OUTDIR}/${HASHFILE}")"

echo
echo "=== DB snapshot complete ==="
echo "  archive : ${OUTDIR}/${ARCHIVE}"
echo "  size    : ${SIZE_HUMAN} (${SIZE_BYTES} bytes)"
echo "  sha256  : ${SHA}"
echo "  sidecar : ${OUTDIR}/${HASHFILE}"
