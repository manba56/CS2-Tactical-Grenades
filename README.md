# CS2 Tactical Grenades

一个面向 CS2 战术和道具管理的全栈项目，包含玩家前台、内容管理后台和 FastAPI 后端。项目适合用来整理地图雷达点位、投掷物线路、战术执行步骤、图片/视频素材和玩家收藏。

## 功能概览

- 玩家前台：热门地图、战术浏览、地图道具雷达、战术详情、收藏和最近浏览。
- 管理后台：地图、道具点位、战术、素材、用户管理。
- 道具点位：后台按“瞄点 + 落点 + 线路”录入，前台按落点聚合多个道具。
- 媒体资料：支持道具瞄点图、站位瞄点图、落点效果图、视频 URL 和图片说明。
- 自动部署：GitHub webhook 触发服务器 `deploy.sh`，后台拉代码、构建前后端并重启 API。

## 项目结构

```text
cs2-tactics-suite/
├─ cs2-api/      # FastAPI 后端
├─ cs2-web/      # Vue 3 玩家前台
├─ cs2-admin/    # Vue 3 管理后台
├─ tests/        # unit / api / e2e 测试
├─ tools/        # 导入、下载和质量检查脚本
├─ deploy/       # 部署辅助配置
└─ deploy.sh     # webhook 实际执行的部署脚本
```

## 快速启动

Windows 一键启动：

```powershell
.\start-all.ps1
```

已安装依赖时可跳过安装：

```powershell
.\start-all.ps1 -SkipInstall
```

停止本地服务：

```powershell
.\stop-all.ps1
```

手动启动 API：

```bash
cd cs2-api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8008
```

手动启动玩家前台：

```bash
cd cs2-web
npm install
npm run dev
```

手动启动管理后台：

```bash
cd cs2-admin
npm install
npm run dev
```

默认地址：

```text
API:   http://127.0.0.1:8008
Web:   http://127.0.0.1:5174
Admin: http://127.0.0.1:5175
```

## 质量检查

推荐使用统一入口：

```powershell
.\tools\quality-check.ps1
```

Linux / 服务器：

```bash
bash tools/quality-check.sh
```

该脚本会运行：

- `tests/unit` 后端单元测试
- `cs2-web` typecheck + build
- `cs2-admin` typecheck + build
- `git diff --check`

更多用法见 [docs/quality-gate.md](docs/quality-gate.md)。

## 测试账号

玩家账号：

```text
demo / demo123
```

后台账号：

```text
admin / admin123
```

## 部署 Webhook

`POST /api/webhook/deploy` 支持两种校验方式：

- GitHub webhook 的 `X-Hub-Signature-256`
- 自建脚本的 `X-Deploy-Secret`

服务器项目根目录建议创建 `.env`：

```bash
DEPLOY_WEBHOOK_SECRET=replace-with-a-long-random-secret
PROJECT_DIR=/www/wwwroot/cs2-tactics
DEPLOY_BRANCH=main
API_SERVICE=cs2-api
```

GitHub Webhook 推荐配置：

```text
Payload URL: https://yourdomain.com/api/webhook/deploy
Content type: application/json
Secret: 与 DEPLOY_WEBHOOK_SECRET 相同
Events: Just the push event
```

`deploy.sh` 会执行：

```text
git pull --ff-only
python3 -m pip install -r cs2-api/requirements.txt
npm ci / npm install
npm run typecheck
npm run build
systemctl restart cs2-api
curl /api/health
```

Webhook 返回 `200` 代表任务已接收；是否真正部署成功，以服务器 `deploy.log` 和 health check 为准：

```bash
cd /www/wwwroot/cs2-tactics
tail -n 120 deploy.log
git -c safe.directory=/www/wwwroot/cs2-tactics rev-parse --short HEAD
curl -i http://127.0.0.1:8008/api/health
```

## API 摘要

公开接口：

- `GET /api/public/home`
- `GET /api/public/maps`
- `GET /api/public/maps/{slug}`
- `GET /api/public/tactics`
- `GET /api/public/tactics/{slug}`
- `POST /api/public/auth/register`
- `POST /api/public/auth/login`
- `GET /api/public/me/favorites`

后台接口：

- `POST /api/admin/auth/login`
- `GET /api/admin/dashboard`
- `GET/POST/PUT /api/admin/maps`
- `GET/POST/PUT /api/admin/points`
- `GET/POST/PUT/DELETE /api/admin/lineups`
- `GET/POST/PUT /api/admin/tactics`
- `POST /api/admin/assets`

## 迭代方向

- 数据层从单文件 SQLite 演进到带迁移的 MySQL / PostgreSQL。
- 后端拆分 `main.py`，把 auth、public、admin、deploy 路由分模块。
- 前后台抽取共享枚举和标签，减少地图、阵营、道具类型的重复定义。
- 补充核心 API / E2E 验收，覆盖地图雷达、道具媒体、战术详情和部署 webhook。
- 完善生产配置、备份策略、日志保留和素材清理。
