#!/usr/bin/env bash
# Run on the droplet after git pull (also used by GitHub Actions).
set -euo pipefail

APP_DIR="${APP_DIR:-/home/deploy/anyone-email}"
cd "$APP_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -r requirements.txt -q
playwright install chromium 2>/dev/null || true

mkdir -p data

if systemctl is-active --quiet anyone-email 2>/dev/null; then
  sudo systemctl restart anyone-email
  sleep 4
  curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null
  echo "Deploy OK — anyone-email restarted."
else
  echo "Deploy OK — .venv updated (systemd service not running yet)."
fi
