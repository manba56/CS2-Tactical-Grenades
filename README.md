# CS2 Tactical Grenades

一个面向 `CS2 / CSGO` 战术整理与道具配合的全栈项目，包含：

- 玩家前台：按地图浏览战术、道具线路、执行步骤
- 内容后台：维护地图、点位、线路、战术、资源和前台用户
- 轻量后端：提供登录、收藏、最近浏览、内容管理和资源上传接口

适合用来做：

- 队伍训练战术手册
- 约战前的默认道具复盘
- 社区型战术资料站的 MVP 原型

## Features

- 地图优先浏览：从地图进入，再按阵营、道具类型、难度和标签筛选
- 战术详情页：展示目标、阶段、参与人数、步骤顺序、所需道具和关联线路
- 收藏与最近浏览：前台用户可登录后保存常看战术
- 后台内容管理：支持地图、点位、线路、战术、媒体、用户六类管理
- 图片资源上传：适合站位图、瞄点图、结果图等内容维护
- 种子数据内置：开箱即可看到 Mirage / Inferno / Nuke 示例内容

## Project Structure

```text
cs2-tactics-suite/
├─ cs2-api/     # FastAPI 后端
├─ cs2-web/     # Vue 3 玩家前台
└─ cs2-admin/   # Vue 3 管理后台
```

### `cs2-api`

- 技术栈：`Python 3.13`、`FastAPI`
- 当前存储：本地 SQLite 数据库，首次启动自动写入种子数据
- 主要能力：
  - 前台登录 / 注册
  - 地图 / 战术查询
  - 收藏与最近浏览
  - 后台 CRUD
  - 图片上传

### `cs2-web`

- 技术栈：`Vue 3`、`Vite`、`TypeScript`、`Pinia`
- 页面：
  - 首页
  - 地图库
  - 地图详情
  - 战术详情
  - 收藏页
  - 登录页

### `cs2-admin`

- 技术栈：`Vue 3`、`Vite`、`TypeScript`、`Pinia`
- 模块：
  - 地图管理
  - 点位管理
  - 线路管理
  - 战术管理
  - 媒体资源
  - 前台用户

## Tech Stack

- Backend: `FastAPI`
- Frontend: `Vue 3 + Vite + TypeScript`
- State: `Pinia`
- Data Storage: local `SQLite` database seeded on first start
- Asset Strategy: static image assets + uploaded files

## Quick Start

### One-click Start on Windows

在仓库根目录直接运行：

```powershell
.\start-all.ps1
```

或者双击：

```text
start-all.bat
```

脚本会：

- 检查 `python` 和 `npm` 是否可用
- 自动补装缺失的 `cs2-api` Python 依赖
- 自动补装缺失的 `cs2-web` / `cs2-admin` Node 依赖
- 分别拉起 API、玩家前台、管理后台 3 个窗口

如果你已经装好了依赖，想更快启动：

```powershell
.\start-all.ps1 -SkipInstall
```

关闭这 3 个服务：

```powershell
.\stop-all.ps1
```

### 1. Start API

```bash
cd cs2-api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8008
```

API 默认地址：

```text
http://127.0.0.1:8008
```

### 2. Start Player Web

```bash
cd cs2-web
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5174
```

### 3. Start Admin Panel

```bash
cd cs2-admin
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5175
```

## Quality Checks

后端单元测试：

```bash
cd tests
python -m pytest unit -q
```

玩家前台：

```bash
cd cs2-web
npm run typecheck
npm run build
```

管理后台：

```bash
cd cs2-admin
npm run typecheck
npm run build
```

## Demo Accounts

前台账号：

- `demo / demo123`

后台账号：

- `admin / admin123`

## Current Implementation Notes

- 后端当前使用本地 SQLite 持久化，数据库文件位于 `cs2-api/data/db.sqlite`
- 上传文件会保存到 `cs2-api/app/static/uploads/`
- 地图和线路示例资源位于 `cs2-api/app/static/assets/maps/`
- 前端默认请求 `http://127.0.0.1:8008`
- 部署 webhook 默认关闭；需要配置 `DEPLOY_WEBHOOK_SECRET` 或 `GITHUB_WEBHOOK_SECRET`

### Deployment Webhook

`POST /api/webhook/deploy` 支持两种校验方式：

- GitHub webhook 的 `X-Hub-Signature-256`
- 自建脚本的 `X-Deploy-Secret`

未配置密钥时接口会返回 `503`，避免误暴露后触发部署。

GitHub 仓库 Webhook 推荐配置：

```text
Payload URL: https://yourdomain.com/api/webhook/deploy
Content type: application/json
Secret: 与服务器 DEPLOY_WEBHOOK_SECRET 相同
Events: Just the push event
```

服务器项目根目录建议创建 `.env`：

```bash
DEPLOY_WEBHOOK_SECRET=replace-with-a-long-random-secret
PROJECT_DIR=/www/wwwroot/cs2-tactics
DEPLOY_BRANCH=main
API_SERVICE=cs2-api
```

根目录 `deploy.sh` 是 webhook 实际执行的脚本，会执行：

```text
git pull --ff-only -> install deps -> typecheck -> build -> restart API -> health check
```

如果 API 服务以 `www` 等非 root 用户运行，webhook 进程需要无密码重启服务权限。示例：

```text
www ALL=(root) NOPASSWD: /bin/systemctl restart cs2-api
```

请先用 `which systemctl` 确认服务器上的 `systemctl` 路径，再写入 sudoers。

## API Highlights

公开前台接口：

- `GET /api/public/home`
- `GET /api/public/maps`
- `GET /api/public/maps/{slug}`
- `GET /api/public/tactics`
- `GET /api/public/tactics/{slug}`
- `POST /api/public/auth/register`
- `POST /api/public/auth/login`
- `GET /api/public/me/favorites`

后台管理接口：

- `POST /api/admin/auth/login`
- `GET /api/admin/dashboard`
- `GET/POST/PUT /api/admin/maps`
- `GET/POST/PUT /api/admin/points`
- `GET/POST/PUT/DELETE /api/admin/lineups`
- `GET/POST/PUT /api/admin/tactics`
- `POST /api/admin/assets`

## Roadmap

- [ ] Refine SQLite CRUD or migrate to `MySQL` / `PostgreSQL` for larger deployments
- [ ] Add JWT and stronger auth/session handling
- [ ] Support visual point dragging on map
- [ ] Support richer tactic editor for ordered steps
- [ ] Add deployment config and production env split
- [ ] Add tests for critical API and UI flows

## Development Status

当前版本更适合作为一个可演示、可继续扩展的 MVP：

- 已具备完整的信息架构
- 已具备前后台联动
- 已有示例数据和资源
- 适合继续往数据库、权限、可视化编辑器方向演进

## License

暂未添加。若计划公开长期维护，建议补充 `MIT` 或你偏好的开源协议。
