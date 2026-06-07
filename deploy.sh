#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# CS2 Tactics Suite — 一键更新部署
# ═══════════════════════════════════════════════════════════════
# set -e removed — webhook runs this in background, errors must not kill the script

PROJECT_DIR="/www/wwwroot/cs2-tactics"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║  CS2 Tactics Suite — 一键部署       ║"
echo "╚══════════════════════════════════════╝"

# ── 1. 拉取代码 ──────────────────────────────────
echo "[1/3] 拉取最新代码..."
git checkout main 2>/dev/null || true
git pull origin main 2>&1 || echo "  ⚠ git pull 失败，使用现有代码"

# ── 2. 后端重启 ─────────────────────────────────
echo "[2/3] 重启 API 服务..."
if systemctl is-active cs2-api &>/dev/null; then
    systemctl restart cs2-api
    echo "  ✓ systemctl restart cs2-api"
elif supervisorctl status cs2-api &>/dev/null 2>&1; then
    supervisorctl restart cs2-api
    echo "  ✓ supervisorctl restart cs2-api"
else
    echo "  ⚠ 未找到 cs2-api 服务，跳过（请手动重启）"
fi

# ── 3. 验证 ─────────────────────────────────────
echo "[3/3] 验证服务状态..."
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
