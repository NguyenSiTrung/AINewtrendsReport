#!/usr/bin/env bash
# update.sh — Lightweight code upgrade for AI News & Trends Report
# Usage: sudo bash deploy/update.sh
#
# Use this after pulling new code to the server.
# For first-time setup, use install.sh instead.
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

# ─── Pre-flight ───────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use: sudo bash deploy/update.sh)"
    exit 1
fi

# ─── Configuration ────────────────────────────────────────
APP_USER="ainews"
APP_DIR="/opt/ainews/app"
VENV_DIR="/opt/ainews/venv"
DATA_DIR="/var/lib/ainews"

if [[ ! -d "$APP_DIR" ]]; then
    err "Application not found at $APP_DIR — run install.sh first"
    exit 1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  AI News & Trends Report — Code Update${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# ─── Step 1: Update Python dependencies ──────────────────
info "Updating Python dependencies..."
UV_BIN="/opt/ainews/.local/bin/uv"
if [[ ! -x "$UV_BIN" ]]; then
    UV_BIN="$(sudo -u "$APP_USER" bash -c 'command -v uv')"
fi
cd "$APP_DIR"
sudo -u "$APP_USER" bash -c "UV_PROJECT_ENVIRONMENT=\"$VENV_DIR\" \"$UV_BIN\" sync"
ok "Python dependencies updated via uv"

# ─── Step 2: Run database migrations ─────────────────────
info "Running database migrations..."
cd "$APP_DIR"
sudo -u "$APP_USER" \
    AINEWS_DB_PATH="$DATA_DIR/ainews.db" \
    "$VENV_DIR/bin/alembic" upgrade head 2>/dev/null || {
        warn "Alembic migration failed — database may already be current"
    }
ok "Database migrations complete"

# ─── Step 3: Update systemd units (if changed) ───────────
info "Syncing systemd service files..."
UNITS_CHANGED=false

for unit in ainews-api ainews-worker ainews-beat; do
    src="$APP_DIR/deploy/systemd/${unit}.service"
    dst="/etc/systemd/system/${unit}.service"
    if [[ -f "$src" ]]; then
        if ! cmp -s "$src" "$dst" 2>/dev/null; then
            cp "$src" "$dst"
            UNITS_CHANGED=true
            info "  Updated ${unit}.service"
        fi
    fi
done

if [[ "$UNITS_CHANGED" == "true" ]]; then
    systemctl daemon-reload
    ok "Systemd units updated and reloaded"
else
    ok "Systemd units unchanged"
fi

# ─── Step 4: Restart services ────────────────────────────
info "Restarting services..."

SERVICES=(ainews-api ainews-worker ainews-beat)
for svc in "${SERVICES[@]}"; do
    if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
        systemctl restart "$svc"
        ok "  Restarted $svc"
    else
        warn "  $svc is not enabled — skipping"
    fi
done

# ─── Step 5: Health check ────────────────────────────────
info "Waiting for API to start..."
sleep 3

if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    ok "Health check passed ✓"
else
    warn "Health check failed — API may still be starting (check: journalctl -u ainews-api -f)"
fi

# ─── Summary ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Update complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Verify services:"
echo "    systemctl status ainews-api ainews-worker ainews-beat"
echo "    journalctl -u ainews-api -f"
echo ""
