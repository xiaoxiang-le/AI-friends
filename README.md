# AI friends

AI角色创作与对话平台，采用Vue3、Django6和LangGraph。支持账号与资料、角色草稿/发布/归档、好友、流式文字聊天、语音气泡、长期记忆和角色知识文件。

## 文档

- [产品需求、设计、业务流程与原43项任务核对](docs/PRODUCT.md)
- [2026-10-10功能验收和剩余事项](docs/ACCEPTANCE.md)
- [本地运行、配置与部署](LOCAL_RUN.md)
- [2026-10-11按功能提交清单](docs/COMMITS-2026-10-11.md)

## 当前能力与验证边界

文字、TTS、ASR与时间工具已有本地真实服务验证。角色知识文件支持TXT/Markdown，默认本地关键词检索；独立嵌入配置可启用混合检索。个人音色复刻已有授权上传、任务、查询、删除和引用保护，但当前没有公网HTTPS样本环境，尚未真实供应商验收。自动记忆默认关闭。

每个角色选择一个预设/个人音色，也可仅文字。语音回复先显示气泡，右键或更多菜单展开原回复文字；历史音频为私有资源。归档角色与移除好友保留消息。

本轮后端81项、前端9项测试通过；浏览器验收使用Codex内置浏览器，Chrome扩展连接受阻。收藏、推荐、标签、运营看板仍属P2规划。不能将本地验收等同于生产部署或所有设备通过。

## 快速开始

要求Python **3.12+**，Node.js 20.19+或22.12+。在项目根目录（Windows PowerShell）：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
Copy-Item backend/.env.example backend/.env
& .\.venv\Scripts\python.exe backend/manage.py migrate
cd frontend
npm ci
npm run build
cd ..
.\start-local.ps1
```

复制.env只用于首次配置，不要覆盖已有密钥文件。填入账号可用的文字与语音配置后重启后端和worker。开发页为http://127.0.0.1:5173，打包页面为http://127.0.0.1:8000。启动脚本同时启动持久化任务worker，日志与PID写入.local。

## 验证

```powershell
& .\.venv\Scripts\python.exe backend/manage.py check
& .\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe backend/manage.py test web --noinput
cd frontend
npm test
npm run build
```

自动测试隔离数据库、文件与外部服务，不自动使用真实账号密钥。真实服务验收需另行验证文本、语音识别、播放及复刻。

## 项目结构

```text
backend/web/models/               角色、消息、知识、任务、审计等
backend/web/services/             供应商配置、音色、检索、任务与私有文件
backend/web/views/resources.py    知识、个人音色、任务、举报、健康接口
backend/web/management/commands/  run_jobs持久化工作器
frontend/src/views/create/        创作中心、角色编辑、资源管理
frontend/src/components/character/chat_field/  文字、语音、记忆与历史
docs/                            产品与验收文档
requirements-runtime.txt         当前核心运行依赖
start-local.ps1                  本地三服务启动
nginx.conf                       生产配置示例，部署前替换并验证
```

## 配置与生产环境

以backend/.env.example为准；DeepSeek文字密钥与阿里云语音密钥分开配置。音色中文名称在backend/web/services/voice_catalog.py修改。

runserver仅用于本地开发，不是生产部署方案。生产使用WSGI服务、Nginx与独立run_jobs守护进程，设置DJANGO_DEBUG=false、强密钥、域名白名单及HTTPS。Nginx示例包含SSE关闭缓冲、超时、限流与私有目录阻断，需在目标服务器执行nginx -t。数据库、media和private_storage均纳入备份；密钥、私人音频及样本不提交Git。
