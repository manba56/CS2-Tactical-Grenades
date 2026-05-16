#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Jenkins Docker 一键部署脚本（在宝塔终端执行）
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

# ── 1. 检查 Docker ──────────────────────────────────────
if ! command -v docker &> /dev/null; then
    warn "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker && systemctl start docker
    log "Docker 安装完成"
fi

# ── 2. 构建并启动 ───────────────────────────────────────
log "构建 Jenkins 镜像（含 Python + pytest + Allure）..."
docker compose build --no-cache

log "启动 Jenkins 容器..."
docker compose up -d

# ── 3. 等待 Jenkins 就绪 ────────────────────────────────
log "等待 Jenkins 启动（约 15-30 秒）..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/login > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

# ── 4. 获取初始密码 ─────────────────────────────────────
INITIAL_PW=$(docker compose exec -T jenkins cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null || echo "")
if [ -n "$INITIAL_PW" ]; then
    log "初始管理员密码: ${INITIAL_PW}"
else
    warn "无法自动获取初始密码，请手动执行："
    warn "  docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
fi

# ── 5. 打印访问信息 ─────────────────────────────────────
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "你的服务器IP")

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Jenkins 已部署完成"
echo "══════════════════════════════════════════════════════"
echo "  Web UI:  http://${SERVER_IP}:8080"
echo "  初始密码: ${INITIAL_PW:-见上方提示}"
echo ""
echo "  项目路径（容器内）: /opt/cs2-tactics-suite"
echo "  测试脚本:          /opt/cs2-tactics-suite/tests/run.sh"
echo ""
echo "  下一步:"
echo "  1. 浏览器打开 http://${SERVER_IP}:8080"
echo "  2. 输入初始密码 → 创建管理员账号"
echo "  3. 新建 Pipeline Job → 指向 /opt/cs2-tactics-suite"
echo "  4. Jenkinsfile 路径: Jenkinsfile"
echo "══════════════════════════════════════════════════════"

# ── 6. 防火墙提示 ───────────────────────────────────────
warn "如果外网无法访问 8080 端口，请在宝塔面板放行:"
warn "  安全 → 防火墙 → 添加 8080 端口"
