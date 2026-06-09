#!/bin/bash
# CS2 Tactics Suite - Deployment Script
# Run on your Alibaba Cloud server (NOT on your local machine)
#
# Usage: bash deploy.sh
# This will: build frontends, install deps, start API, configure Nginx

set -e

PROJECT_DIR="/www/wwwroot/cs2-tactics"
API_DIR="$PROJECT_DIR/cs2-api"
WEB_DIR="$PROJECT_DIR/cs2-web"
ADMIN_DIR="$PROJECT_DIR/cs2-admin"
SERVICE_USER="www"

echo "=== CS2 Tactics Suite Deploy ==="

# ── 1. Copy project to server ───────────────────────
# (You should upload the entire cs2-tactics-suite folder
#  to /www/wwwroot/cs2-tactics first via Baota file manager or SFTP)

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: $PROJECT_DIR not found."
    echo "Please upload the cs2-tactics-suite folder to /www/wwwroot/ first."
    exit 1
fi

echo "[0/4] Preparing runtime permissions..."
mkdir -p "$API_DIR/data" "$API_DIR/app/static/uploads"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
chmod -R u+rwX,g+rwX "$API_DIR/data" "$API_DIR/app/static/uploads"

# ── 2. Install Python deps ──────────────────────────
echo "[1/4] Installing Python dependencies..."
cd "$API_DIR"
python3 -m pip install -r requirements.txt

# ── 3. Build frontends ──────────────────────────────
echo "[2/4] Building cs2-web (player frontend)..."
cd "$WEB_DIR"
npm install
npm run build

echo "[3/4] Building cs2-admin (management panel)..."
cd "$ADMIN_DIR"
npm install
npm run build

# ── 4. Start/restart API service ────────────────────
echo "[4/4] Setting up API service..."

# Create systemd service
cat > /etc/systemd/system/cs2-api.service << 'SERVICE'
[Unit]
Description=CS2 Tactics API
After=network.target

[Service]
Type=simple
User=www
WorkingDirectory=/www/wwwroot/cs2-tactics/cs2-api
EnvironmentFile=-/www/wwwroot/cs2-tactics/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8008
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable cs2-api
systemctl restart cs2-api

echo "[4/4] Granting webhook restart permission..."
SYSTEMCTL_PATH="$(command -v systemctl)"
SUDOERS_FILE="/etc/sudoers.d/cs2-deploy"
cat > "$SUDOERS_FILE" << SUDOERS
$SERVICE_USER ALL=(root) NOPASSWD: $SYSTEMCTL_PATH restart cs2-api
SUDOERS
chmod 440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE"

echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo "1. Edit /www/server/panel/vhost/nginx/yourdomain.com.conf"
echo "   - Replace the content with deploy/nginx-cs2.conf"
echo "   - Change 'yourdomain.com' to your actual domain or IP"
echo "2. Restart Nginx: nginx -s reload"
echo "3. Check API status: systemctl status cs2-api"
echo ""
echo "Access:"
echo "  Frontend:  http://yourdomain.com/"
echo "  Admin:     http://yourdomain.com/admin/"
echo "  API:       http://yourdomain.com/api/"
echo ""
echo "Default admin login: admin / admin123"
