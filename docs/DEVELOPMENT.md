# 本地开发与测试

[返回项目首页](../README.md) · [环境配置](CONFIGURATION.md) · [Docker部署](DEPLOYMENT.md)

本指南适用于需要修改代码的本机开发。服务器容器部署不需要先安装本机Python或Node，也不需要运行本指南的三服务启动器。

## 运行环境

| 工具/服务 | 要求 | 用途 |
|---|---|---|
| Git | 已安装，可访问仓库 | 获取和更新代码 |
| Python | **3.12 及以上** | Django 后端和任务工作器 |
| Node.js | **20.x 且不低于 20.19，或 22.12 及以上** | 前端安装、开发和构建；21.x 不符合当前 engines |
| npm | 随 Node.js 安装 | 安装 package-lock.json 锁定的前端依赖 |
| 数据库 | 默认 SQLite，无需另装数据库服务 | 存储账号、角色、消息和任务 |
| 文字 API | 支持 OpenAI 兼容聊天接口，需有效密钥、基础地址和模型名称 | 启用 AI 回复，可切换供应商及模型 |
| 语音 API | 可选；需兼容项目的 DashScope WebSocket 协议 | 启用 ASR/TTS |

检查本机版本：

```text
git --version
python --version
node --version
npm --version
```

Windows 如果 `python` 不可用，可以用 `py -3 --version` 检查，再将下文创建虚拟环境的 `python` 换成 `py -3`。macOS/Linux 可使用 `python3`。先确认选中的 Python 满足版本要求。

## 首次安装

以下步骤先安装依赖，再配置服务，最后启动。已经安装的项目更新方法见[停止、重启与更新](#停止重启与更新)，**不要再次覆盖已有 `.env`**。

第一次运行请按下表顺序操作；配置说明较长，可以先完成最小配置，再按需要开启语音等功能。

| 顺序 | 操作 | 完成标志 |
|---|---|---|
| 1 | 获取代码，进入项目根目录 | 当前目录能看到 `README.md`、`backend`、`frontend` |
| 2 | 创建 `.venv` 并安装后端依赖 | pip 命令正常结束，没有安装失败信息 |
| 3 | 在 `frontend` 中执行 `npm ci`，再回到根目录 | npm 命令正常结束，生成 `frontend/node_modules` |
| 4 | 复制并编辑 `backend/.env` | 文件名正确；需要 AI 回复时已填写文字服务三项配置 |
| 5 | 执行数据库迁移、前端构建和 Django 检查 | 迁移成功、构建成功，检查没有错误 |
| 6 | 按[启动与访问](#启动与访问)启动服务 | 后端、前端和任务工作器均在运行 |
| 7 | 打开 `http://127.0.0.1:5173/`，注册并创建角色 | 能登录、保存角色；配置文字 API 后能收到 AI 回复 |

每个命令块按顺序执行；如果某条命令报错，先处理报错，再继续下一步。**已在 IDE 中打开或解压了本项目的用户，直接使用当前项目文件夹，跳过 `git clone`。** 文件夹名称不必是 `AI-friends`，以本机实际路径为准。

### 1. 获取项目

```text
git clone https://github.com/xiaoxiang-le/AI-friends.git
cd AI-friends
```

下面除明确要求进入 `frontend` 的步骤外，都从仓库根目录执行。

在 VS Code 中可通过“终端 → 新建终端”打开 PowerShell；用 `Get-Location` 查看当前目录。如果不在项目根目录，先执行 `Set-Location "你的项目完整路径"`（替换为真实路径；路径含空格时保留引号）。macOS/Linux 使用 `pwd` 查看目录、`cd "你的项目完整路径"` 切换目录。

### 2. 创建 Python 环境并安装后端依赖

Windows PowerShell：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
```

macOS/Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-runtime.txt
```

使用根目录的 `requirements-runtime.txt` 安装当前运行依赖。根目录和 `backend/requirements.txt` 仅作为指向该清单的兼容入口；历史完整环境快照归档到 `docs/archive/environments/`，不用于安装。不要只安装 Django。直接指定 `.venv` 中的 Python，无需先激活环境。

### 3. 安装前端依赖

各平台均执行：

```text
cd frontend
npm ci
cd ..
```

`npm ci` 使用仓库中的锁文件。完成后应有 `frontend/node_modules`。项目通过 `predev` / `prebuild` 将 VAD 模型和 WASM 从本地依赖复制到 `frontend/public/vad`，不用手工下载模型。

### 4. 创建配置文件

Windows PowerShell：

```powershell
if (!(Test-Path -LiteralPath backend/.env)) {
    Copy-Item -LiteralPath backend/.env.example -Destination backend/.env
}
notepad backend/.env
```

macOS/Linux：

```bash
test -f backend/.env || cp backend/.env.example backend/.env
# 使用编辑器打开 backend/.env，按[环境配置](CONFIGURATION.md)填写。
```

文件必须是 **`backend/.env`**，不是根目录 `.env`，也不是 `.env.txt`。供应商密钥由后端读取，不填写到前端文件中。

### 5. 初始化数据库并构建页面

配置完成后，Windows PowerShell：

```powershell
& .\.venv\Scripts\python.exe backend/manage.py migrate --noinput
cd frontend
npm run build
cd ..
& .\.venv\Scripts\python.exe backend/manage.py check
```

macOS/Linux：

```bash
.venv/bin/python backend/manage.py migrate --noinput
cd frontend
npm run build
cd ..
.venv/bin/python backend/manage.py check
```

迁移会建立账号、角色、消息、任务等表以及默认音色。首次构建前，Django可能提示 `staticfiles.W004`（静态目录尚不存在）；先完成build，再运行check核对。构建会生成 `backend/static/frontend` 并自动更新 Django 的入口模板。仅安装依赖而不构建时，8000 端口的打包页面可能无法加载；5173 开发页面由 Vite 提供。

迁移输出中的 `OK` 或 `No migrations to apply` 都表示该步骤已完成；前端应显示构建成功，最后的 `check` 应没有错误。完成后继续“启动与访问”，这些安装命令本身不会启动网站。

## 启动与访问

### Windows：一键启动

完成安装、配置和构建后，在根目录执行：

```powershell
.\start-local.ps1
```

脚本要求8000和5173端口空闲；启动Django、Vite和任务worker，记录日志与PID。若PowerShell策略禁止运行脚本，可使用下面的手动方式，不必修改系统全局执行策略。

脚本会在后台启动三个服务，打印前后端地址和日志目录后返回命令提示符，这是正常行为；不会自动打开浏览器。等待服务启动后，手动打开 `http://127.0.0.1:5173/`。如果暂时无法访问，先检查下方日志，不要连续重复执行启动脚本。

```powershell
Get-Content -LiteralPath .local/backend-error.log -Tail 50
Get-Content -LiteralPath .local/frontend.log -Tail 50
Get-Content -LiteralPath .local/frontend-error.log -Tail 50
Get-Content -LiteralPath .local/jobs-error.log -Tail 50
```

### Windows：手动启动

打开三个终端，**每个终端先进入仓库根目录**。不要在一个终端逐行运行三个长期进程。

三个终端运行期间都要保持打开。推荐依次启动后端、任务工作器和前端；某个终端报错退出时，先修复该服务，再重新执行对应命令。

终端1：Django后端。

```powershell
& .\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
```

终端2：任务worker。

```powershell
& .\.venv\Scripts\python.exe backend/manage.py run_jobs
```

终端3：前端开发服务。

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

后端终端出现 `Starting development server at http://127.0.0.1:8000/`，前端终端显示 `http://127.0.0.1:5173/`，表示这两个服务已开始监听。任务工作器会持续等待任务，没有输出也可能是正常状态；如果命令直接退出或显示异常堆栈，则需要处理报错。

### macOS/Linux：手动启动

同样使用三个终端，每个终端从仓库根目录开始：

```bash
# 终端1
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload
```

```bash
# 终端2
.venv/bin/python backend/manage.py run_jobs
```

```bash
# 终端3
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

| 地址 | 用途 | 依赖 |
|---|---|---|
| http://127.0.0.1:5173/ | 前端开发页面，支持热更新 | Vite + Django |
| http://127.0.0.1:8000/ | 打包页面 | 已build + Django |
| http://127.0.0.1:8000/admin/ | 管理后台 | Django + 管理员账号 |
| http://127.0.0.1:8000/api/capabilities/ | 查看配置是否完整 | Django；不需要登录 |

首次访问先注册账号。可按“创作中心 → 新建角色 → 保存草稿 → 开始聊天”验证基础流程，再选择角色语音回复或语音输入。知识索引、复刻和自动摘要需要worker；只开Django和Vite会使这些任务停在排队状态。

建议按以下顺序确认运行结果：

1. 打开 `http://127.0.0.1:5173/`，确认页面正常显示。
2. 注册普通账号并登录，刷新页面，确认登录状态保留。
3. 创建角色并保存草稿，进入聊天，发送一句文字；已配置文字服务时，应看到 AI 回复。未配置语音时，先使用仅文字模式。
4. 需要语音时，再配置 ASR/TTS、重启后端与工作器，验证音色试听和麦克风录音；浏览器询问麦克风权限时允许使用。

页面能打开只说明前端可访问；注册登录成功才能验证后端和数据库连接，收到 AI 回复才能验证文字服务配置。

创建管理员（不是普通用户注册的必需步骤）：

```powershell
& .\.venv\Scripts\python.exe backend/manage.py createsuperuser
```

macOS/Linux将解释器替换为 `.venv/bin/python`。管理员用户名和密码由你自行输入。

## 停止、重启与更新

### 手动启动的服务

在对应终端按 `Ctrl+C` 停止；重新执行各自启动命令。`.env` 修改后重启后端与worker；`--noreload`模式修改Python代码也需要重启。

### 一键启动的服务

从根目录查看启动记录和命令行：

```powershell
$runInfo = Get-Content -LiteralPath .local/pids.json -Raw | ConvertFrom-Json
$allProcesses = Get-CimInstance Win32_Process
$allProcesses | Where-Object {
    $_.ProcessId -in @($runInfo.backend, $runInfo.frontend, $runInfo.jobs) -or
    $_.ParentProcessId -in @($runInfo.backend, $runInfo.jobs)
} | Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine
```

确认输出中的进程确实属于本项目后，用 `Stop-Process -Id 你核对过的进程号` 停止相应启动器及Python子进程。PID可能被系统重复使用，不要直接停止全部python/node进程。全部停止后重新运行 `start-local.ps1`。

日志包括 `.local/backend-error.log`、`.local/frontend-error.log`、`.local/jobs-error.log` 及对应标准输出日志。例如：

```powershell
Get-Content -LiteralPath .local/backend-error.log -Tail 80
Get-Content -LiteralPath .local/jobs-error.log -Tail 80
```

手动启动时日志主要显示在各终端中。

### 更新已有安装

先停止服务并备份数据，确认已有代码修改已提交或另行保存，再执行：

```powershell
git pull --ff-only origin main
& .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
& .\.venv\Scripts\python.exe backend/manage.py migrate --noinput
cd frontend
npm ci
npm run build
cd ..
.\start-local.ps1
```

macOS/Linux使用对应解释器，随后按手动方式启动。新增环境字段从模板对照补入现有 `.env`，不覆盖密钥。`--ff-only`遇到分叉会停止；先检查分支差异再决定合并。新build后重启无重载Django，以免缓存入口模板仍引用旧JS/CSS。

## 检查配置与运行测试

Windows PowerShell，从根目录执行：

```powershell
& .\.venv\Scripts\python.exe backend/manage.py check
& .\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe backend/manage.py test web --noinput
cd frontend
npm test
npm run build
cd ..
```

macOS/Linux使用 `.venv/bin/python` 替换解释器。截至2026-10-11，容器化改动后的后端回归为89项通过；前端最近一次功能回归为9项通过，证据保留在[验收报告](../docs/ACCEPTANCE.md)。这不代表所有设备及未来供应商模型均已经验收。

服务运行后查看能力配置：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/capabilities/ | ConvertTo-Json -Depth 6
```

macOS/Linux可执行 `curl http://127.0.0.1:8000/api/capabilities/`。`configured=true`只说明字段完整；接口不实时调用供应商，`verified=false`不是“已经测试失败”。是否实际可用要通过聊天、试听和录音验证。

## 常见问题

| 问题 | 检查与处理 |
|---|---|
| 注册报错或提示表不存在 | 确认使用.venv解释器，执行migrate并查看Django日志；默认SQLite不需要外部数据库账号 |
| AI提示未配置 | 检查backend/.env及AI三个字段；确认没有保存成.env.txt，重启后端/worker |
| 已配置却401/403 | 核对对应供应商密钥、地域、接口权限；不要把DeepSeek密钥用于阿里云语音 |
| 模型不存在/不支持工具 | 核对账号实际模型；必要时关闭AI_ENABLE_TOOLS；当前ASR模板使用FunASR而非强制旧Gummy |
| 页面空白或JS/CSS 404 | 安装前端依赖并build，检查Django模板引用，重启无重载后端；Vite开发页用5173 |
| npm/依赖安装失败 | 检查Node版本与仓库根/前端目录，前端执行npm ci；后端不要只安装Django |
| 8000/5173被占用 | 检查现有服务/进程归属，停止本项目旧服务；默认脚本不自行抢占或换端口 |
| 任务一直排队 | 启动run_jobs，查看jobs日志及任务错误；配置更新后worker也要重启 |
| 删除角色失败、请求返回404 HTML | 旧后端可能仍未加载新增删除路由；核对当前运行的项目目录，停止旧后端后重新启动。不要只刷新前端，也不要在旧进程未退出时重复启动服务 |
| 删除角色返回JSON错误/409 | 按返回原因处理：角色已更新先刷新；生成回复或知识/记忆任务运行中需等待结束。永久删除会清理所有用户与该角色的聊天和资料，需要保留历史时使用归档 |
| 浏览器不能录音 | 检查麦克风权限/设备，远程站点使用HTTPS；检查本地VAD模型和WASM请求 |
| 语音无法自动播放 | 浏览器可能限制自动播放，点击气泡播放；TTS失败时保留文字 |
| 登录后刷新退出/CORS错误 | 统一127.0.0.1或统一localhost，核对CORS来源；本地HTTP保持DEBUGtrue |
| 复刻提示未配置 | 除TTS外还要VOICE_URL和公网HTTPS PUBLIC_BASE_URL；普通预设音色不需要复刻配置 |
| 知识内容没有被引用 | 检查角色关联、文档任务是否完成和检索相关性；关键词检索不是所有问法都必然命中 |
| 生产反复HTTPS重定向 | 核对可信代理的X-Forwarded-Proto及DJANGO_TRUST_PROXY配置，不关闭HTTPS保护来掩盖代理配置错误 |
