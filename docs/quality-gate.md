# 质量门禁与发布检查

第四阶段的目标是让项目进入“每次改完都能被验证”的状态。以后改前台、后台或部署脚本，先跑质量门禁，再提交和触发 webhook。

## 本地一键检查

Windows:

```powershell
.\tools\quality-check.ps1
```

Linux / 服务器:

```bash
bash tools/quality-check.sh
```

检查内容：

- 后端单元测试：`tests/unit`
- 玩家前台：`npm run typecheck`、`npm run build`
- 管理后台：`npm run typecheck`、`npm run build`
- Git 空白字符检查：`git diff --check`

如果当前环境没有安装 `pytest-timeout`，脚本会自动跳过 `--timeout=60`，避免 pytest 报 `unknown config option: timeout`。

## 常用快速模式

只检查后端：

```powershell
.\tools\quality-check.ps1 -SkipFrontend
```

只检查前端：

```powershell
.\tools\quality-check.ps1 -SkipBackend
```

跳过生产构建，只跑类型检查和单元测试：

```powershell
.\tools\quality-check.ps1 -SkipBuild
```

Linux 参数对应为：

```bash
bash tools/quality-check.sh --skip-frontend
bash tools/quality-check.sh --skip-backend
bash tools/quality-check.sh --skip-build
```

## 部署后验证

GitHub webhook 返回 `200` 只代表“部署任务已接收”。真正部署是否完成，要看服务器：

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

如果 webhook 超时但服务器日志继续构建，优先确认当前代码是否已经变成 GitHub 最新提交；新版 webhook 会尽快返回，并把耗时构建放到后台执行。

## 提交前建议

小改动至少跑：

```powershell
.\tools\quality-check.ps1 -SkipBuild
```

涉及前台页面、后台页面、部署脚本或 API 返回结构时，跑完整检查：

```powershell
.\tools\quality-check.ps1
```
