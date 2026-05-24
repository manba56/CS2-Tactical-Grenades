#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# 同步数据库：服务器 → 本地
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── 配置（改成你自己的）───────────────────────────
SERVER="你的服务器IP"
API_PORT="8008"
ADMIN_USER="admin"
ADMIN_PASS="Gyh159951."

# ── 目标路径 ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$SCRIPT_DIR/cs2-api/data/db.sqlite"

echo "[1/2] 登录获取 token..."
TOKEN=$(curl -sf -X POST "http://${SERVER}:${API_PORT}/api/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}" | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

echo "[2/2] 下载数据库..."
curl -sf -o "$DB_PATH" \
  -H "Authorization: Bearer $TOKEN" \
  "http://${SERVER}:${API_PORT}/api/admin/db/export"

echo "✓ 已保存到: $DB_PATH"
ls -lh "$DB_PATH"
