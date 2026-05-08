#!/usr/bin/env bash
# install.sh — Idempotent deployment bootstrap for AI News & Trends Report
# Target: Ubuntu 22.04 / 24.04 LTS, local server, HTTP-only
# Usage: sudo bash deploy/install.sh
#
# Safe to re-run on upgrades: creates only what's missing,
# updates code + deps, and restarts services gracefully.
set -euo pipefail

# ─── Colour helpers ───────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Colour

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── Pre-flight checks ───────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (use: sudo bash deploy/install.sh)"
    exit 1
fi

# Detect Ubuntu version
if [[ ! -f /etc/os-release ]]; then
    err "Cannot detect OS — /etc/os-release not found"
    exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    err "Unsupported OS: $ID. This installer targets Ubuntu only."
    exit 1
fi

UBUNTU_VERSION="$VERSION_ID"
case "$UBUNTU_VERSION" in
    22.04|24.04)
        info "Detected Ubuntu $UBUNTU_VERSION ($VERSION_CODENAME)"
        ;;
    *)
        err "Unsupported Ubuntu version: $UBUNTU_VERSION (supported: 22.04, 24.04)"
        exit 1
        ;;
esac

# ─── Configuration ────────────────────────────────────────
APP_USER="ainews"
APP_HOME="/opt/ainews"
APP_DIR="$APP_HOME/app"
VENV_DIR="$APP_HOME/venv"
DATA_DIR="/var/lib/ainews"
LOG_DIR="/var/log/ainews"
CONFIG_DIR="/etc/ainews"
BACKUP_DIR="/var/backups/ainews"
REPORTS_DIR="$DATA_DIR/reports"
ENV_FILE="$CONFIG_DIR/ainews.env"

# Resolve deploy directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── Step 1: Install system packages ─────────────────────
info "Installing system packages..."

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

PACKAGES=(
    python3.12
    python3.12-venv
    python3.12-dev
    python3-pip
    sqlite3
    build-essential
    libssl-dev
    curl
    git
    fonts-liberation
)

apt-get install -y -qq "${PACKAGES[@]}"
ok "System packages installed"

# ─── Step 2: Install Valkey ───────────────────────
info "Installing Valkey..."

if command -v valkey-server &>/dev/null; then
    ok "Valkey already installed: $(valkey-server --version 2>/dev/null | head -1)"
else
    # Install Valkey from official PPA
    if curl -fsSL https://packages.valkey.io/gpg 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/valkey-archive-keyring.gpg 2>/dev/null; then
        echo "deb [signed-by=/usr/share/keyrings/valkey-archive-keyring.gpg] https://packages.valkey.io/deb stable main" \
            > /etc/apt/sources.list.d/valkey.list
        apt-get update -qq
        if apt-get install -y -qq valkey-server 2>/dev/null; then
            ok "Valkey installed from official PPA"
        else
            err "Failed to install Valkey from PPA."
            exit 1
        fi
    else
        err "Failed to add Valkey GPG key."
        exit 1
    fi
fi

# Ensure the service is enabled and running
if systemctl list-unit-files valkey-server.service &>/dev/null; then
    systemctl enable valkey-server 2>/dev/null || true
    systemctl start valkey-server 2>/dev/null || true
fi

# ─── Step 3: Create system user ──────────────────────────
info "Ensuring system user '$APP_USER' exists..."

if id "$APP_USER" &>/dev/null; then
    ok "User '$APP_USER' already exists"
else
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_HOME" --create-home "$APP_USER"
    ok "Created system user '$APP_USER'"
fi

# ─── Step 4: Create directory layout ─────────────────────
info "Creating directory layout..."

declare -A DIR_PERMS=(
    ["$APP_HOME"]="0755"
    ["$DATA_DIR"]="0750"
    ["$REPORTS_DIR"]="0750"
    ["$LOG_DIR"]="0750"
    ["$CONFIG_DIR"]="0755"
    ["$BACKUP_DIR"]="0750"
)

for dir in "${!DIR_PERMS[@]}"; do
    mkdir -p "$dir"
    chown "$APP_USER:$APP_USER" "$dir"
    chmod "${DIR_PERMS[$dir]}" "$dir"
done

ok "Directory layout ready"

# ─── Step 5: Clone / update repository ───────────────────
info "Deploying application code..."

if [[ -d "$APP_DIR/.git" ]]; then
    # Update existing installation
    info "Updating existing installation at $APP_DIR..."
    cd "$APP_DIR"
    sudo -u "$APP_USER" git pull --ff-only 2>/dev/null || {
        warn "git pull failed — copying from local repo instead"
        rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
            "$REPO_ROOT/" "$APP_DIR/"
        chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    }
else
    # Fresh install: copy from the repo this script lives in
    info "Copying application from $REPO_ROOT to $APP_DIR..."
    mkdir -p "$APP_DIR"
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
        --exclude='node_modules' --exclude='.agents' --exclude='.beads' \
        --exclude='.claude' --exclude='conductor' \
        "$REPO_ROOT/" "$APP_DIR/"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

ok "Application code deployed to $APP_DIR"

# ─── Step 6: Create virtualenv and install ────────────────
info "Setting up Python virtualenv..."

if [[ ! -d "$VENV_DIR" ]]; then
    sudo -u "$APP_USER" python3.12 -m venv "$VENV_DIR"
    ok "Virtualenv created at $VENV_DIR"
else
    ok "Virtualenv already exists at $VENV_DIR"
fi

sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --quiet -e "$APP_DIR"
ok "Python dependencies installed"

# ─── Step 7: Environment file ────────────────────────────
info "Checking environment file..."

if [[ -f "$ENV_FILE" ]]; then
    ok "Environment file already exists at $ENV_FILE (not overwritten)"
else
    cp "$APP_DIR/.env.example" "$ENV_FILE"
    # Update paths for production
    sed -i 's|AINEWS_DB_PATH=.*|AINEWS_DB_PATH=/var/lib/ainews/ainews.db|' "$ENV_FILE"
    ok "Installed .env.example → $ENV_FILE (edit before starting services!)"
fi

# Set secure ownership regardless
chown root:"$APP_USER" "$ENV_FILE"
chmod 0640 "$ENV_FILE"

# ─── Step 8: Database migration & seed ────────────────────
info "Running database migrations..."

cd "$APP_DIR"
sudo -u "$APP_USER" \
    AINEWS_DB_PATH="$DATA_DIR/ainews.db" \
    "$VENV_DIR/bin/alembic" upgrade head 2>/dev/null || {
        warn "Alembic migration failed — database may already be current"
    }

info "Seeding database..."
sudo -u "$APP_USER" \
    AINEWS_DB_PATH="$DATA_DIR/ainews.db" \
    "$VENV_DIR/bin/ainews" seed 2>/dev/null || {
        warn "Seed may have already been applied"
    }

ok "Database ready"

# ─── Step 9: Install systemd units ───────────────────────
info "Installing systemd service units..."

cp "$APP_DIR/deploy/systemd/ainews-api.service" /etc/systemd/system/
cp "$APP_DIR/deploy/systemd/ainews-worker.service" /etc/systemd/system/
cp "$APP_DIR/deploy/systemd/ainews-beat.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable ainews-api ainews-worker 2>/dev/null
ok "Systemd units installed and enabled (not started — configure env first)"

# ─── Step 10: Install cron files ──────────────────────────
info "Installing cron schedules..."

cp "$APP_DIR/deploy/cron/ainews" /etc/cron.d/ainews
cp "$APP_DIR/deploy/cron/ainews-backup" /etc/cron.d/ainews-backup
chmod 0644 /etc/cron.d/ainews /etc/cron.d/ainews-backup
ok "Cron schedules installed"

# Make backup script executable
chmod +x "$APP_DIR/deploy/scripts/backup_db.sh"

# ─── Step 11: Install logrotate config ────────────────────
info "Installing logrotate configuration..."

cp "$APP_DIR/deploy/logrotate/ainews" /etc/logrotate.d/ainews
chmod 0644 /etc/logrotate.d/ainews
ok "Logrotate configuration installed"

# ─── Step 12: File-mode audit ─────────────────────────────
info "Running file-mode audit..."

AUDIT_PASS=true

_audit_mode() {
    local path="$1" expected="$2" desc="$3"
    if [[ -e "$path" ]]; then
        actual=$(stat -c "%a" "$path")
        if [[ "$actual" == "$expected" ]]; then
            ok "  $desc: $path ($actual)"
        else
            warn "  $desc: $path is $actual (expected $expected)"
            AUDIT_PASS=false
        fi
    fi
}

_audit_mode "$ENV_FILE" "640" "Config file"
_audit_mode "$DATA_DIR/ainews.db" "640" "Database file" 2>/dev/null || true
_audit_mode "$DATA_DIR" "750" "Data directory"
_audit_mode "$REPORTS_DIR" "750" "Reports directory"
_audit_mode "$LOG_DIR" "750" "Log directory"

if [[ "$AUDIT_PASS" == "true" ]]; then
    ok "File-mode audit passed"
else
    warn "Some file modes need attention (see above)"
fi

# ─── Step 13: Restart services if running (upgrade path) ──
if systemctl is-active --quiet ainews-api; then
    info "Restarting services for upgrade..."
    systemctl restart ainews-api ainews-worker
    ok "Services restarted"
fi

# ─── Summary ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  AI News & Trends Report — Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Next steps:"
echo "  1. Edit configuration:  sudo nano $ENV_FILE"
echo "  2. Start services:      sudo systemctl start ainews-api ainews-worker"
echo "  3. Verify health:       curl http://localhost:8000/api/health"
echo ""
echo "  Service management:"
echo "    systemctl status ainews-api"
echo "    systemctl status ainews-worker"
echo "    journalctl -u ainews-api -f"
echo ""
echo "  Log files:  $LOG_DIR/"
echo "  Database:   $DATA_DIR/ainews.db"
echo "  Backups:    $BACKUP_DIR/"
echo ""
