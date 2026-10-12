# 贡献指南

感谢参与 AI friends。首次安装、环境配置及部署统一见[README](README.md)，设计约束见[产品文档](docs/PRODUCT.md)，已有测试证据见[验收报告](docs/ACCEPTANCE.md)。

## 开发环境

使用 Python 3.12+ 与满足 `frontend/package.json` engines 的 Node.js。后端依赖以 `requirements-runtime.txt` 为准，前端使用 `npm ci` 和锁文件。推荐 VS Code 配合 Vue (Official) 扩展；调试组件可使用 Vue Devtools。前端模板原有的安装和构建说明已统一到根 README。

在自己的分支开发，按单个功能组织改动。先查看 `git status`，确认当前目录属于目标仓库，避免改动其他项目或覆盖未提交的工作。

## 修改与验证

保持现有 Vue 组件、Django 模型/服务/视图职责分层。修改数据模型时提交对应迁移；修改接口时同时检查权限、参数校验、错误状态与前端调用。密钥只在后端加载，不放入前端构建。

Windows PowerShell，从仓库根目录执行：

```powershell
& .\.venv\Scripts\python.exe backend/manage.py check
& .\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe backend/manage.py test web --noinput
cd frontend
npm test
npm run build
cd ..
git diff --check
```

macOS/Linux 用 `.venv/bin/python` 替换 Python 路径。按改动范围选择验证；纯文档整理检查相对链接、目录树和配置路径即可，不必为文字改动新增测试。构建会更新 Django 入口模板，提交前检查生成差异。

容器改动还需执行 `docker compose config --quiet`；生产覆盖的校验和真实容器启动步骤见 README。不要公开 `config` 展开后的密钥。记录实际执行的测试及未验收条件，避免把模拟测试或配置检查写成真实服务验收。

## 提交与合并

提交标题采用 `feat`、`fix`、`build`、`docs`、`test` 或 `chore` 前缀，并说明对应功能；正文解释原因与验证结果。一个提交处理一个明确功能，避免把无关重构和业务修改混在一起。

推送前获取远程最新代码，检查分支差异。个人开发分支可合并 `origin/main`：

```text
git fetch origin
git merge origin/main
```

发生冲突时逐项理解双方改动，完成修复并重新验证后再提交。不要直接用一方文件覆盖另一方，也不要对共享 `main` 强制推送。优先通过 Pull Request 说明问题、实现与验证；仓库维护者授权直接推送时仍需核对远程更新。

## 文档与问题报告

仅根目录保留 `README.md`；配置及部署步骤集中在 README，设计更新 `docs/PRODUCT.md`，有日期的测试证据更新 `docs/ACCEPTANCE.md`，功能变化记入 `CHANGELOG.md`。过时资料移至 `docs/archive/` 并标明不作为当前操作依据，移动文件时同步修复引用。

普通问题通过 [Issues](https://github.com/xiaoxiang-le/AI-friends/issues) 提交，包含环境版本、复现步骤、预期与实际结果、脱敏日志。安全问题遵循[安全说明](SECURITY.md)。不要上传真实 `.env`、个人数据库、音频、样本或证书私钥。
