#!/usr/bin/env bash
# install.sh — Simplified local development/server setup for AI News
# Safe to re-run.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

if ! command -v valkey-server &>/dev/null; then
    info "Adding Valkey repository and installing..."
    curl -fsSL https://serverless.industries/public.key | sudo gpg --dearmor -o /usr/share/keyrings/valkey.gpg
    echo "deb [signed-by=/usr/share/keyrings/valkey.gpg] https://serverless.industries/valkey/apt $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/valkey.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq valkey-server
fi

info "Ensuring Valkey is running..."
sudo systemctl enable valkey-server 2>/dev/null || true
sudo systemctl start valkey-server 2>/dev/null || true
ok "Valkey is running"

info "Setting up Python environment with uv..."
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv sync
ok "Dependencies installed"

info "Checking environment file..."
if [[ ! -f ".env" ]]; then
    cp ".env.example" ".env"
    ok "Created .env from .env.example (please review settings if needed)"
else
    ok ".env already exists"
fi

info "Running database migrations..."
uv run alembic upgrade head

info "Seeding database..."
uv run ainews seed

info "Ensuring admin user exists..."
# Create admin if not exists
uv run ainews seed admin --email admin@example.com --password changeme || true
ok "Database setup complete"

info "Configuring systemd background services..."

# Get current user and absolute path to the project
CURRENT_USER=$(whoami)
APP_DIR=$(pwd)
UV_BIN=$(command -v uv)

sudo tee /etc/systemd/system/ainews-api.service > /dev/null <<EOF
[Unit]
Description=AI News API Server
After=network.target valkey-server.service

[Service]
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$UV_BIN run uvicorn ainews.api.main:app --host 0.0.0.0 --port 1210
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/ainews-worker.service > /dev/null <<EOF
[Unit]
Description=AI News Celery Worker
After=network.target valkey-server.service

[Service]
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$UV_BIN run celery -A ainews.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/ainews-beat.service > /dev/null <<EOF
[Unit]
Description=AI News Celery Beat
After=network.target valkey-server.service

[Service]
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$UV_BIN run celery -A ainews.tasks.celery_app beat --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ainews-api ainews-worker ainews-beat
sudo systemctl restart ainews-api ainews-worker ainews-beat
ok "Systemd services configured and started"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Local Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  The application is now running in the background 24/7."
echo ""
echo "  Service Management:"
echo "    sudo systemctl restart ainews-api ainews-worker ainews-beat"
echo "    sudo systemctl stop ainews-api ainews-worker ainews-beat"
echo ""
echo "  View Logs:"
echo "    sudo journalctl -u ainews-api -f"
echo "    sudo journalctl -u ainews-worker -f"
echo "    sudo journalctl -u ainews-beat -f"
echo ""
echo "  Default Admin Login: admin@example.com / changeme"
echo ""
