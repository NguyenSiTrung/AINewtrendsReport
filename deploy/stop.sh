#!/usr/bin/env bash
# stop.sh — Stop all AI News systemd services.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

info "Stopping AI News services..."
sudo systemctl stop ainews-beat ainews-worker ainews-api 2>/dev/null || true
ok "All services stopped"

echo ""
echo -e "${GREEN}Service Status:${NC}"
for svc in ainews-api ainews-worker ainews-beat; do
    status=$(systemctl is-active "$svc" 2>/dev/null || true)
    if [[ "$status" == "active" ]]; then
        echo -e "  ${RED}●${NC} $svc — still running"
    else
        echo -e "  ${GREEN}●${NC} $svc — stopped"
    fi
done

echo ""
echo "  To restart:  sudo systemctl start ainews-api ainews-worker ainews-beat"
echo ""
