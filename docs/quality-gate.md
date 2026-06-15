# 质量门禁与发布检查

这个质量门禁的目标是：每次改完前台、后台、接口或部署脚本，都能用固定命令快速确认“没有明显回归”，再提交和触发 webhook。

## 本地命令

Windows:

```powershell
.\tools\quality-check.ps1
```

Linux / 服务器:

```bash
bash tools/quality-check.sh
```

默认 `full` 模式会检查：

- 后端单元测试：`tests/unit`
- 玩家前台：`npm run test:unit`、`npm run typecheck`、`npm run build`
- 管理后台：`npm run typecheck`、`npm run build`
- Git 空白字符检查：`git diff --check`

如果当前环境没有安装 `pytest-timeout`，脚本会自动跳过 `--timeout=60`，避免 pytest 提示 unknown config option。

## 分层模式

快速模式：跳过生产构建，适合开发中频繁自测。

```powershell
.\tools\quality-check.ps1 -Mode quick
```

```bash
bash tools/quality-check.sh --quick
```

完整模式：默认模式。

```powershell
.\tools\quality-check.ps1 -Mode full
```

发布模式：显式的完整发布前检查。

```powershell
.\tools\quality-check.ps1 -Mode release
```

冒烟模式：只跑最轻的后端冒烟目标，并跳过生产构建。

```powershell
.\tools\quality-check.ps1 -Mode smoke
```

```bash
bash tools/quality-check.sh --smoke
```

## 常用参数

只检查后端：

```powershell
.\tools\quality-check.ps1 -SkipFrontend
```

只检查前端：

```powershell
.\tools\quality-check.ps1 -SkipBackend
```

跳过生产构建：

```powershell
.\tools\quality-check.ps1 -SkipBuild
```

Linux 对应参数：

```bash
bash tools/quality-check.sh --skip-frontend
bash tools/quality-check.sh --skip-backend
bash tools/quality-check.sh --skip-build
```

## 部署后验证

GitHub webhook 返回 `200` 只代表“部署任务已接收”。真正是否部署完成，要看服务器：

```bash
cd /www/wwwroot/cs2-tactics
tail -n 120 deploy.log
git -c safe.directory=/www/wwwroot/cs2-tactics rev-parse --short HEAD
systemctl status cs2-api --no-pager
curl -i http://127.0.0.1:8008/api/health
```

成功时日志末尾应看到：

```text
API health check passed
Deployment completed successfully
```
