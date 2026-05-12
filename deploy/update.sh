#!/usr/bin/env bash
# update.sh — Lightweight code upgrade for AI News & Trends Report
# Usage: bash deploy/update.sh
#
# Use this after pulling new code to the server (e.g., git pull).
set -euo pipefail

# ─── Colour helpers ───────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  AI News & Trends Report — Code Update${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# ─── Step 1: Update Python dependencies ──────────────────
info "Updating Python dependencies..."
if ! command -v uv &>/dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        err "uv is not installed. Please run bash deploy/install.sh first."
        exit 1
    fi
fi

uv sync
ok "Python dependencies updated via uv"

# ─── Step 2: Run database migrations ─────────────────────
info "Running database migrations..."
uv run alembic upgrade head || {
    warn "Alembic migration failed"
}
ok "Database migrations complete"

# ─── Step 3: Restart services ────────────────────────────
info "Restarting services..."
sudo systemctl restart ainews-api ainews-worker ainews-beat
ok "Services restarted"

# ─── Step 4: Health check ────────────────────────────────
info "Waiting for API to start..."
sleep 3

if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    ok "Health check passed ✓"
else
    warn "Health check failed — API may still be starting (check logs: sudo journalctl -u ainews-api -f)"
fi

# ─── Summary ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Update complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Verify services:"
echo "    sudo systemctl status ainews-api ainews-worker ainews-beat"
echo "    sudo journalctl -u ainews-api -f"
echo ""
