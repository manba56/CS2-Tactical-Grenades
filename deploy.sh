#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# CS2 Tactics Suite — 一键更新部署
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT_DIR="/www/wwwroot/cs2-tactics"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║  CS2 Tactics Suite — 一键部署       ║"
echo "╚══════════════════════════════════════╝"

# ── 1. 拉取代码 ──────────────────────────────────
echo "[1/5] 拉取最新代码..."
git checkout main 2>/dev/null || true
git pull origin main 2>&1 || echo "  ⚠ git pull 失败，使用现有代码"

# ── 2. 后端重启 ─────────────────────────────────
echo "[2/5] 重启 API 服务..."
if systemctl is-active cs2-api &>/dev/null; then
    systemctl restart cs2-api
    echo "  ✓ systemctl restart cs2-api"
elif supervisorctl status cs2-api &>/dev/null 2>&1; then
    supervisorctl restart cs2-api
    echo "  ✓ supervisorctl restart cs2-api"
else
    echo "  ⚠ 未找到 cs2-api 服务，跳过（请手动重启）"
fi

# ── 3. 构建管理后台 ─────────────────────────────
echo "[3/5] 构建管理后台..."
cd "$PROJECT_DIR/cs2-admin" || { echo "  ✗ cs2-admin 目录不存在"; }
if [ -f package.json ]; then
  npm install --silent 2>/dev/null || npm install || true
  npm run build 2>&1 || echo "  ✗ 管理后台构建失败"
else
  echo "  ⚠ 未找到 package.json，跳过"
fi

# ── 4. 构建玩家端 ───────────────────────────────
echo "[4/5] 构建玩家端..."
cd "$PROJECT_DIR/cs2-web" || { echo "  ✗ cs2-web 目录不存在"; }
if [ -f package.json ]; then
  npm install --silent 2>/dev/null || npm install || true
  npm run build 2>&1 || echo "  ✗ 玩家端构建失败"
else
  echo "  ⚠ 未找到 package.json，跳过"
fi

# ── 5. 验证 ─────────────────────────────────────
echo "[5/5] 验证服务状态..."
sleep 1
if curl -sf http://127.0.0.1:8008/api/health > /dev/null; then
    echo "  ✓ API 服务正常"
else
    echo "  ✗ API 服务异常，请检查日志"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  部署完成 ✓                         ║"
echo "╚══════════════════════════════════════╝"
