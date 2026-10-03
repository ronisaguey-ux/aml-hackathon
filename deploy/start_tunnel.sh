#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${WORKSPACE_DIR}/data"
mkdir -p "${DATA_DIR}"

LOG_FILE="${DATA_DIR}/tunnel.log"
URL_FILE="${DATA_DIR}/public_url.txt"

CLOUDFLARED_BIN="$(which cloudflared 2>/dev/null || echo "/home/roni-saguey/.local/bin/cloudflared")"

if [[ ! -x "${CLOUDFLARED_BIN}" ]]; then
    echo "Error: cloudflared binary not found at ${CLOUDFLARED_BIN}" >&2
    exit 1
fi

echo "Starting Cloudflare quick tunnel for AxiomMem on http://localhost:8000..."
exec "${CLOUDFLARED_BIN}" tunnel --url http://localhost:8000 --logfile "${LOG_FILE}"
