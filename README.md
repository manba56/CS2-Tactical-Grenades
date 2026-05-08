# CS2 Tactics Suite

CS2 战术道具配合网站的独立仓库，包含三个模块：

- `cs2-api`: `FastAPI` 后端，提供地图、战术、收藏、后台管理、资源上传接口
- `cs2-web`: 玩家前台站点，按地图浏览战术与道具线路
- `cs2-admin`: 内容管理后台，维护地图、点位、线路、战术、资源和前台用户

## 技术栈

- 后端：`Python 3.13`、`FastAPI`、本地 JSON 种子数据
- 前端：`Vue 3`、`Vite`、`TypeScript`

## 本地启动

### 1. 启动后端

```bash
cd cs2-api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8008
```

### 2. 启动玩家前台

```bash
cd cs2-web
npm install
npm run dev
```

### 3. 启动后台管理

```bash
cd cs2-admin
npm install
npm run dev
```

## 默认演示账号

- 前台：`demo / demo123`
- 后台：`admin / admin123`

## 说明

- 当前后端默认使用本地 JSON 持久化，首次启动会自动初始化种子数据。
- 上传资源保存到 `cs2-api/app/static/uploads/`。
- 如需正式部署，建议下一步替换为 `SQLite` 或 `MySQL`，并补充 JWT、密码加密和生产配置。
