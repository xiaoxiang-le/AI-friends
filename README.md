# AI friends

AI friends 是一个 AI 角色创作与对话项目。用户可以创建角色，设置形象、性格、音色和知识资料，通过文字或语音与角色交流，并继续查看历史对话。

后端使用 Django 6、Django REST Framework、SimpleJWT 和 LangGraph，前端使用 Vue 3、Vite、Pinia。默认数据库是本机 SQLite。**文字聊天支持通过 OpenAI 兼容 API 接入不同供应商的大模型**，可在配置文件中设置 API Key、基础地址和模型名称。文字与语音服务独立配置。

当前语音识别与合成采用 DashScope WebSocket 任务协议。接入其他语音服务时，需要兼容该协议，或修改后端适配代码；文字模型的可替换性不代表任意语音 API 都能直接使用。

## 文档导航

| 文档 | 内容 |
|---|---|
| [部署指南](docs/DEPLOYMENT.md) | Docker首次启动、服务器HTTPS、统一Nginx、备份更新及排错 |
| [环境配置](docs/CONFIGURATION.md) | `.env`字段、AI/语音接入、回退关系及可选功能 |
| [本地开发](docs/DEVELOPMENT.md) | Python/Node安装、三服务启动、构建和测试 |
| [产品文档](docs/PRODUCT.md) | 设计、权限、流程与规划 |
| [验收报告](docs/ACCEPTANCE.md) | 已执行测试与尚未完成的验收 |
| [贡献指南](CONTRIBUTING.md) / [安全说明](SECURITY.md) | 提交与协作、安全问题报告 |
| [更新记录](CHANGELOG.md) / [历史资料](docs/archive/INDEX.md) | 当前变化及历史快照 |
| [许可证](LICENSE) | MIT授权 |

## 项目结构

下面展示仓库中维护的代码、配置及文档；`.env`、数据库、上传文件、虚拟环境和构建产物不提交。

```text
AI-friends/
├── backend/                          # Django 后端
│   ├── backend/                      # 项目配置、主路由、WSGI / ASGI
│   ├── web/                          # 业务应用
│   │   ├── models/                   # 账号、角色、消息、知识与任务模型
│   │   ├── services/                 # 供应商配置、音色、检索与任务服务
│   │   ├── views/                    # 账号、角色、聊天及资源 API
│   │   ├── management/commands/      # run_jobs 后台工作器
│   │   ├── migrations/               # 数据库迁移与默认音色
│   │   ├── templates/                # Django 页面入口
│   │   ├── urls.py                   # API 路由
│   │   └── tests.py                  # 后端回归测试
│   ├── media/user/photos/default.png # 运行及容器初始化使用的默认头像
│   ├── .env.example                  # 应用配置模板
│   ├── requirements.txt              # 后端依赖兼容入口
│   └── manage.py                     # Django 管理入口
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── components/               # 聊天、语音、导航等组件
│   │   ├── views/                    # 账号、角色、资源与个人页面
│   │   ├── router/                   # 页面路由与登录守卫
│   │   ├── stores/                   # Pinia 用户状态
│   │   └── js/                       # HTTP、SSE 和通用工具
│   ├── public/                       # 公共资源；VAD 构建时生成
│   ├── tests/                        # 前端回归测试
│   ├── package.json                  # npm 命令与依赖
│   ├── package-lock.json             # 锁定依赖版本
│   └── vite.config.js                # 开发代理与构建输出
├── docker/                           # 容器运行配置与辅助程序
│   ├── initialize.py                 # 目录检查、头像、迁移与静态初始化
│   ├── healthcheck.py                # Web 与 worker 健康探针
│   ├── nginx.conf                    # 本机 HTTP 网关
│   ├── nginx.production.conf.template # HTTPS 网关模板
│   ├── nginx.gateway.conf.template    # 统一 HTTPS 网关后的项目代理
│   ├── nginx.shared-gateway.conf.example # 宿主机统一 Nginx 站点示例
│   ├── gateway.env.example            # 统一网关域名、来源和端口模板
│   ├── production.env.example        # 域名与证书目录模板
│   └── requirements.txt              # 容器附加 Gunicorn 依赖
├── deploy/legacy/                    # 非容器 uWSGI / Nginx 备选示例
├── scripts/                          # VAD 准备与构建入口同步
├── docs/
│   ├── DEPLOYMENT.md                 # Docker与服务器部署、排错
│   ├── DEVELOPMENT.md                # 本机安装、开发与测试
│   ├── CONFIGURATION.md              # AI、语音和可选功能配置
│   ├── PRODUCT.md                    # 产品设计、权限、流程与规划
│   ├── ACCEPTANCE.md                 # 测试证据、限制与待验收项
│   ├── screenshots/                  # README 页面演示图片
│   └── archive/                      # 历史课程、交付与环境快照
├── Dockerfile                        # 前端、后端和网关多阶段镜像
├── .dockerignore                     # 排除密钥、本机依赖及运行数据
├── compose.yaml                      # 本机容器编排
├── compose.production.yaml           # HTTPS 生产覆盖配置
├── requirements-runtime.txt          # 后端运行依赖权威清单
├── requirements.txt                  # 根目录依赖兼容入口
├── start-local.ps1                   # Windows 三服务启动
├── deploy-frontend.ps1               # 前端构建与上传服务器的辅助脚本
├── CONTRIBUTING.md                   # 开发、测试与提交规范
├── SECURITY.md                       # 安全问题报告与配置要求
├── CHANGELOG.md                      # 维护中的更新记录
├── LICENSE                           # MIT 许可证
└── README.md                         # 唯一安装、配置与部署入口
```

音色中文名称在 `backend/web/services/voice_catalog.py` 的 `VOICE_NAMES` 中修改；供应商 voice_id 与展示名分开，改名不等于新增音色。

## 功能概览

| 功能 | 当前实现 |
|---|---|
| 账号与资料 | 注册、登录、刷新登录状态、退出、头像和简介编辑 |
| 角色管理 | 创建、编辑、私有草稿、发布范围、可选审核、归档与恢复、二次确认永久删除 |
| 好友与历史 | 继续会话，归档保留完整消息、语音及知识来源 |
| 文字聊天 | 流式回复、发送/停止按钮、失败重试、请求去重、时间工具 |
| 语音输入与回复 | 录音识别、角色语音气泡、播放、展开原回复文字 |
| 角色音色 | 多种预设音色、试听、选择、更换；每个角色选择一个音色或仅文字 |
| 角色知识 | UTF-8 TXT/Markdown 文件上传、后台索引、关键词检索；可选向量检索 |
| 长期记忆 | 查看、编辑、清空、会话开关；可选后台自动摘要 |
| 个人音色复刻 | 授权样本上传、任务查询、引用保护、删除流程，需要额外外部配置 |
| 基础管理 | Django admin、举报反馈、任务状态、管理员健康接口 |

当前文字、语音合成、ASR 测试样本和知识问答已有本地真实调用证据。个人音色复刻、真实人声设备、可选嵌入、自动摘要及生产环境的剩余验收条件见[验收报告](docs/ACCEPTANCE.md)。收藏、标签、推荐和运营看板属于后续规划。

## Docker运行

**本机快速验证**，先进入仓库根目录。Linux首次复制配置（已有文件不覆盖）：

```bash
test -f backend/.env || cp backend/.env.example backend/.env
```

Windows PowerShell：

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

编辑 `backend/.env` 后启动；API留空也能注册、登录和管理角色：

```text
docker compose up --build -d
docker compose ps -a
```

本机打开 `http://127.0.0.1:8080/`。init应退出码0，web/worker/nginx应为healthy。**远程服务器IP或域名访问请直接按[服务器部署指南](docs/DEPLOYMENT.md#先选访问方式)配置公网入口**，不能把这个本机地址当成公网地址。

## 本地终端运行

如果你想在本机开发调试、修改代码或本地测试，可以不使用 Docker，直接在终端启动后端、任务工作器和前端。

先准备环境：Python 3.12+、Node.js 20.x/22.x 及 npm。然后在仓库根目录执行：

Windows PowerShell：

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
cd frontend
npm ci
cd ..
& .\.venv\Scripts\python.exe backend/manage.py migrate --noinput
cd frontend
npm run build
cd ..
& .\.venv\Scripts\python.exe backend/manage.py check
```

macOS / Linux：

```bash
test -f backend/.env || cp backend/.env.example backend/.env
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-runtime.txt
cd frontend
npm ci
cd ..
.venv/bin/python backend/manage.py migrate --noinput
cd frontend
npm run build
cd ..
.venv/bin/python backend/manage.py check
```

配置好 `backend/.env` 后，按下面方式启动三个服务：

```powershell
# 终端1：Django 后端
& .\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload

# 终端2：任务工作器
& .\.venv\Scripts\python.exe backend/manage.py run_jobs

# 终端3：前端开发服务
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

macOS / Linux：

```bash
# 终端1
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload

# 终端2
.venv/bin/python backend/manage.py run_jobs

# 终端3
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

服务正常启动后，打开 `http://127.0.0.1:5173/` 即可访问前端；后端接口地址为 `http://127.0.0.1:8000/`。更完整的本地开发步骤和排错说明见 [本地开发指南](docs/DEVELOPMENT.md)。

## 配置 backend/.env

文字聊天填写 `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`；语音识别和回复分别填写 `ASR_*`、`TTS_*`。配置模板为[backend/.env.example](backend/.env.example)，完整字段与可选功能见[环境配置](docs/CONFIGURATION.md)。修改后需要重新创建容器，刷新浏览器不会重新加载配置。

## 系统运行演示

本地演示截图；新安装需自行注册并创建角色。

图1：登录与注册页面，用户可创建账号并进入系统。

![登录与注册](docs/screenshots/login.png)

图2：发现角色页面，展示可浏览的角色卡片和入口。

![发现角色](docs/screenshots/discover.png)

图3：文字与语音聊天界面，用户可以输入文本、语音对话并收听角色回复。

![文字与语音聊天](docs/screenshots/chat-voice.png)

图4：知识与音色资源页，用于管理角色知识、音色和相关素材。

![知识与音色资源](docs/screenshots/creation-resources.png)

图5：个人主页，展示用户资料、角色状态和个人设置入口。

![个人主页](docs/screenshots/profile.png)
