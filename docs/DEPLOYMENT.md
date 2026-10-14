# Docker 与服务器部署

[返回项目首页](../README.md) · [环境配置](CONFIGURATION.md) · [本地开发](DEVELOPMENT.md)

## 先选访问方式

| 目标 | 使用方式 | 用户访问地址 |
|---|---|---|
| 本机验证，或先检查服务器内部是否正常 | 基础 `compose.yaml` | 部署机器上的 `http://127.0.0.1:8080/` |
| 远程服务器单独运行本网站 | [HTTPS生产覆盖](#6-服务器-https-部署)，公开80/443 | `https://你的实际域名/` |
| 服务器已有Nginx，或运行多个网站 | [宿主机统一网关](#多项目共用统一-nginx)，转发本机项目端口 | 统一网关配置的HTTPS域名 |

**在服务器上执行基础Compose，不代表外部电脑能访问服务器IP的8080端口。** 基础配置绑定 `127.0.0.1`，Gunicorn的8000只在容器网络中开放。若80/443已被其他网站占用，选择统一网关方案，不让两个Nginx争用同一端口。

还没有域名或证书时，先在服务器执行 `curl -f http://127.0.0.1:8080/api/health/` 检查。需要从自己电脑浏览内部HTTP网站，可建立SSH隧道：

```text
ssh -N -L 18080:127.0.0.1:8080 用户名@服务器IP
```

保持该终端运行，在自己电脑打开 `http://127.0.0.1:18080/`。替换用户名和IP；正式对外使用按下文配置HTTPS。

## 启动失败先检查

从有 `compose.yaml` 的仓库根目录执行：

```text
docker version
docker compose version
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=100 init web worker nginx
```

第一次执行前先复制并配置 `backend/.env`，具体命令在下一节。已有服务器配置不得覆盖。**`docker compose -d`缺少子命令，正确的是 `docker compose up -d`；拉取了Dockerfile或代码改动后使用 `up --build -d`。** 生产模式执行这些命令时必须带同样的 `--env-file` 和 `-f` 参数。

| 现象 | 原因与处理 |
|---|---|
| 缺少 `backend/.env` | 克隆不会带上密钥文件，首次从模板复制后编辑 |
| `Control server error: Permission denied: '/home/app'` | 旧镜像的Gunicorn默认创建HOME下的控制套接字；app用户未创建该目录。本项目已用 `--no-control-socket` 关闭未使用的控制接口，保持非root运行；拉取修复后重建镜像，不能仅restart旧容器 |
| 健康接口持续返回200 | 已说明HTTP后端和账号表查询可用，该日志不能证明整个网站启动失败，也不能证明公网网关或外部AI服务可用 |
| Nginx提示 `/docker-entrypoint.d/ is not empty` | 官方镜像的正常初始化提示；继续查看后面的 `[emerg]` 等错误和容器状态 |
| 服务器内部能访问，外部IP访问不了8080 | 基础模式只绑定127.0.0.1，按HTTPS覆盖或统一网关配置公网入口 |
| 外部域名仍无法访问 | 核对域名解析、云安全组/宿主机防火墙80/443、证书目录与Nginx状态；后台healthy不代表公网已放通 |
| 容器启动后未看到页面 | 正确入口是Nginx的8080或生产80/443，不是宿主机8000；执行curl验证服务器内部入口 |
| 更新时worker迟迟不退出 | 旧工作器作为PID 1未处理SIGTERM，会等到180秒强制停止；修复后收到停止信号会结束当前任务再退出，空闲时及时退出。拉取后重建镜像；正在处理外部服务任务时仍需等待任务完成 |

Gunicorn通过Compose/进程信号管理，本项目不使用`gunicornc`控制接口。关闭控制套接字不会关闭HTTP服务、健康探测或正常的优雅退出。参考[Gunicorn控制配置](https://gunicorn.org/reference/settings/#control-socket-disable)、[Compose启动命令](https://docs.docker.com/reference/cli/docker/compose/up/)。

## Docker运行

以下步骤提供本机HTTP验证、单网站HTTPS和统一网关三种方式。仓库提供多阶段 [Dockerfile](../Dockerfile)、[Compose配置](../compose.yaml)和[服务器HTTPS覆盖配置](../compose.production.yaml)。下面先在本机完成 HTTP 容器部署，再说明服务器 HTTPS 部署。所有命令均从项目根目录执行。

### 1. 准备 Docker 环境

- Windows/macOS：安装 Docker Desktop，启动后等待引擎就绪；Windows 使用 Linux 容器模式，根据安装提示完成 WSL 2 配置。
- Linux 服务器：安装 Docker Engine 和 Docker Compose 插件。
- 本项目要求 Compose **2.30 及以上**，统一使用 `docker compose` 命令。
- 构建时需要访问镜像仓库、npm 和 PyPI；本机无需另外安装 Python、Node.js、虚拟环境或执行 `npm ci`。

在终端检查：

```text
docker version
docker compose version
docker info
```

`docker version` 应显示 Client 和 Server 信息，`docker info` 应正常返回引擎信息。如果提示无法连接 Docker daemon，先启动 Docker Desktop 或 Linux Docker 服务，再继续。

### 2. 准备应用配置

已有 `backend/.env` 时继续使用，不要覆盖。首次部署可复制模板：

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
# 用编辑器打开 backend/.env。
```

按[配置 backend/.env](CONFIGURATION.md#配置-backendenv)填写所选服务的文字 API 密钥、基础地址和模型；语音及可选功能按需配置。只验证注册登录和角色管理时，可以不填外部 API。**本机 HTTP 部署**确认以下设置：

```dotenv
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_TRUST_PROXY=false
```

Compose 自动设置 `DJANGO_DATA_DIR=/data`，不要改为本机 Windows 路径。密钥通过 `env_file` 在容器启动时注入，不作为镜像构建参数。若值包含字面量 `$`，按 Compose 规则用单引号保护。配置检查使用 `config --quiet`，避免输出展开后的密钥。

### 3. 构建并启动容器

```text
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=80 init web worker nginx
```

`config --quiet` 成功时通常没有输出。`--build` 构建镜像，`-d` 在后台运行；首次需要下载镜像和依赖，耗时取决于网络。若命令失败，先查看报错，再继续下一步。

| 服务 | 作用 | 正常状态 |
|---|---|---|
| `init` | 检查数据目录、执行迁移、收集静态文件 | 完成后 `Exited (0)`，属于正常退出 |
| `web` | Gunicorn 运行 Django 后端 | `Up`，健康检查最终为 `healthy` |
| `worker` | 执行知识索引、记忆和音色任务 | `Up`，健康检查最终为 `healthy` |
| `nginx` | 提供页面资源、公开图片和聊天流代理 | `Up`，健康检查最终为 `healthy` |

启动顺序为 `init` 完成 → `web` 与 `worker` 启动 → 后端健康 → `nginx` 启动。刚启动时显示 `starting` 可等待后再执行 `docker compose ps -a`；如果 `init` 非零退出或服务持续 `unhealthy`，检查对应日志。健康检查失败不会单独触发自动重启。

### 4. 访问并验证

打开 http://127.0.0.1:8080/。容器方案已构建前端，无需运行 `start-local.ps1`、Vite 或本机 Django；默认不占用本机 8000/5173 端口。

1. 注册新账号并登录，刷新页面确认登录状态保留。
2. 创建角色、保存并进入聊天；配置文字 API 后确认能收到流式回复。
3. 按需测试音色试听、录音和知识文件上传，确认后台任务可以完成。
4. 停止并重新启动容器后，确认账号、角色和历史消息仍在。

可检查健康接口，但该接口不会验证外部模型服务是否可调用：

```text
curl http://127.0.0.1:8080/api/health/
```

需要管理员账号时执行：

```text
docker compose exec web python manage.py createsuperuser
```

按提示创建账号后访问 http://127.0.0.1:8080/admin/ 。

### 5. 日常管理与数据保留

```text
# 查看服务状态
docker compose ps -a
# 持续查看日志，Ctrl+C 只退出日志查看
docker compose logs -f --tail=80 web worker nginx
# 停止并移除容器，保留数据卷
docker compose down
# 使用现有镜像重新启动
docker compose up -d
```

代码、依赖或 `backend/.env` 更新后，先备份数据，再执行以下命令，使容器重新读取配置、执行迁移并更新页面资源；仅 `restart` 不会读取修改后的 `env_file`：

```text
docker compose down
docker compose up --build -d
docker compose ps -a
```

数据保存在命名卷 `ai-friends_app-data`，通过 `DJANGO_DATA_DIR=/data`统一定位SQLite、media、private_storage和staticfiles。本机不设置该字段时仍沿用backend目录。首次运行建立新数据库，**不会自动导入本机账号或聊天**；导入、备份及HTTPS部署边界见容器说明。`docker compose down`保留数据；`down -v`会删除卷内数据。

不要将本机整个 `backend` 目录挂载到容器的 `/app/backend`，否则会覆盖镜像内构建的页面和代码。导入已有数据需先停止写入服务，一致性备份数据库、图片和私有音频，并确认容器用户 UID 10001 有读写权限；详细边界见[数据管理说明](#docker数据持久化)。

### 6. 服务器 HTTPS 部署

在服务器获取项目代码并准备 Docker 环境。将域名解析到服务器，开放 80/443 端口，并准备匹配域名的 TLS 证书；证书申请和自动续期需要另外管理。

1. 在服务器 `backend/.env` 填写强随机 `DJANGO_SECRET_KEY` 和所需 API 配置。生产覆盖文件会设置 `DJANGO_DEBUG=false`、可信代理和域名白名单。
2. 复制 `docker/production.env.example` 为 `docker/production.env`，填写以下内容：

Linux首次部署可先执行下面的复制命令，再用编辑器修改两份文件（已有文件不覆盖）：

```bash
test -f backend/.env || cp backend/.env.example backend/.env
test -f docker/production.env || cp docker/production.env.example docker/production.env
```

```dotenv
APP_DOMAIN=你的实际域名
TLS_CERT_DIR=/服务器上的证书绝对目录
DOCKER_BIND_IP=0.0.0.0
```

`APP_DOMAIN` 不带协议、端口或路径；证书目录中必须有 `fullchain.pem` 和 `privkey.pem`。`backend/.env` 是应用配置，`docker/production.env` 是 Compose 部署变量，两份文件均不提交到仓库。个人音色复刻启用时，还需设置 `PUBLIC_BASE_URL=https://你的实际域名`。

从服务器项目根目录按顺序执行：

已有部署切换模式前，先用原模式参数执行 `down`（不加 `-v`），停止旧web/worker后再初始化和收集静态资源。例如当前是基础HTTP模式，先执行 `docker compose down`；当前已是生产模式时，down也要带原来的两个 `-f` 和 `--env-file`。首次部署无需这一步。

```bash
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml config --quiet
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml build
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml run --rm --no-deps init
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml run --rm --no-deps nginx nginx -t
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml up -d
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml ps -a
```

先初始化数据卷，再验证 Nginx 配置；每一步成功后继续。访问 `https://你的实际域名/`，确认 HTTP 自动跳转 HTTPS，并验证登录、聊天流和上传功能。生产覆盖文件将本机 8080 入口替换为 80/443；TLS 由容器内 Nginx 提供，Gunicorn 只在容器网络中开放。

生产环境的日志、管理员创建、停止和更新命令，都必须带同样的 `--env-file docker/production.env -f compose.yaml -f compose.production.yaml` 参数。例如查看日志：

```bash
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml logs --tail=80 init web worker nginx
```

不要用 `deploy/legacy/nginx.conf` 替换容器配置：旧示例使用 uWSGI 协议，容器中的 Gunicorn 使用 HTTP 代理。已有外层 HTTPS 网关时需单独调整代理拓扑，见[HTTPS 部署说明](#6-服务器-https-部署)。

### 多项目共用统一 Nginx

多个网站共用服务器时，让宿主机 Nginx 管理公网80/443与证书，各项目使用不同的本机端口。请求路径为：`https://你的域名 → 宿主机 Nginx → 127.0.0.1:8080 → 项目 Nginx → web:8000`。

在 `backend/.env` 设置强随机 `DJANGO_SECRET_KEY` 和应用API凭据。复制 `docker/gateway.env.example` 为 `docker/gateway.env`，填写实际域名、HTTPS来源和本项目端口：

```dotenv
APP_DOMAIN=ai.example.com
APP_HTTP_PORT=8080
APP_DEBUG=false
APP_TRUST_PROXY=true
APP_ORIGIN=https://ai.example.com
NGINX_TEMPLATE=./docker/nginx.gateway.conf.template
```

这些变量用于Compose替换，与应用密钥配置分开。该模式只加载基础Compose，**不要叠加 `compose.production.yaml`**。如果当前使用其他模式，先用原模式参数执行 `down`（不加 `-v`），再执行：

```bash
docker compose --env-file docker/gateway.env config --quiet
docker compose --env-file docker/gateway.env up --build -d
docker compose --env-file docker/gateway.env ps -a
```

按 [宿主机网关示例](../docker/nginx.shared-gateway.conf.example)替换域名、证书路径与转发端口，将server块放入宿主机Nginx的http配置中，执行 `sudo nginx -t` 后再 `sudo systemctl reload nginx`。第二个项目使用8081等不同端口，并同步修改其网关转发地址。证书申请和续期由宿主机网关管理；`APP_ORIGIN`填写用户访问的HTTPS来源，不是内部HTTP端口。

项目端口保持127.0.0.1绑定，后续日志、更新和停止均使用同一 `--env-file docker/gateway.env`。宿主机统一网关模式不能直接用于桥接网络中的网关容器，因为该容器的127.0.0.1指向自身；网关也容器化时需另行配置共享网络及唯一服务别名。

### Docker镜像与健康检查

| 构建阶段/服务 | 职责 |
|---|---|
| `frontend-build` | Node 22 安装锁定依赖、准备 VAD、构建 Vue 并同步 Django 模板 |
| `python-build` | Python 3.12 安装运行依赖及固定版本 Gunicorn |
| `backend / web` | UID 10001 运行 Gunicorn，1 工作进程、4 线程、180 秒超时 |
| `backend / init` | 检查目录写权限、补齐默认头像、迁移和收集静态文件 |
| `backend / worker` | 独立执行 `run_jobs`，与 Web 进程分开管理 |
| `nginx / nginx` | 公开静态文件与图片，使用 HTTP 代理和关闭缓冲的 SSE |

单独构建后端镜像可执行 `docker build --target backend -t ai-friends-backend:local .`。该镜像默认只启动 Gunicorn；迁移、任务和静态网关仍由 Compose 统一启动。

`web` 每15秒检查 `/api/health/` 的账号表查询，`worker` 每30秒检查 PID 1 对应的数据库心跳（5分钟有效窗口），`nginx` 每15秒检查 HTTP 健康入口。健康接口不调用收费供应商；仅此路径豁免 HTTPS 重定向。当前 SQLite 方案只运行一个 worker，不直接横向扩容。每个长期容器最多保留3份、每份10MB日志。

### Docker数据持久化

命名卷 `ai-friends_app-data` 保存数据库、`media`、`private_storage`、`staticfiles`；Nginx只读挂载，私人音频仍通过鉴权或签名端点访问。新卷从后端镜像继承可写目录与默认头像。

迁移已有安装时，先停止本机写入服务，使用 SQLite 一致性备份并同时备份 `media` 和 `private_storage`；停止容器 web/worker，将备份导入卷内对应路径，确保 UID 10001 可读写，再执行 init 迁移和静态收集。先在独立卷验证恢复，不用空库覆盖旧库。单独复制数据库会遗漏图片和语音。

原 Docker 说明已合入本节。容器配置解析和隔离初始化已验证，实际镜像构建、容器启动及证书校验仍需 Docker 环境；证据见[容器验收记录](../docs/ACCEPTANCE.md#2026-10-11-容器化补验)。

### 7. 常见部署问题

| 问题 | 处理 |
|---|---|
| 无法连接 Docker daemon | 确认 Docker 引擎已启动，Windows 使用 Linux 容器模式 |
| 镜像拉取或依赖下载超时 | 检查 Docker 的网络与代理配置，以及镜像仓库、npm、PyPI 的连通性 |
| 8080 被占用 | 停止占用该端口的服务，或修改基础 Compose 的宿主机端口后用新端口访问 |
| `init` 非零退出 | 查看 `docker compose logs --tail=80 init`，检查配置、迁移和卷写权限 |
| 页面能打开但 AI 无回复 | 核对文字 API 三项配置，重建容器以加载配置，并查看 `web` 日志 |
| 任务一直排队 | 检查 `worker` 状态和日志，确认对应外部服务配置可用 |
| 本机 HTTP 被跳转到 HTTPS | 基础 Compose 下保持 `DJANGO_DEBUG=true`；正式 HTTPS 使用生产覆盖文件 |
| HTTPS 服务启动失败 | 检查域名、证书文件名/路径、80/443 占用及 `nginx -t` 输出 |
| 容器中没有本机账号 | 新卷使用新数据库；已有数据需按迁移说明导入 |



## 非容器部署（备选）

`runserver`与5173端口是本地开发方案。优先使用[Docker HTTPS部署](#6-服务器-https-部署)。以下仅为非容器部署的备选方案，需要自行安装及管理WSGI服务、Nginx和独立 `run_jobs` 守护进程；仓库提供[非容器 Nginx 示例](../deploy/legacy/nginx.conf)与[uWSGI示例](../deploy/legacy/uwsgi.ini)，需要替换实际域名、证书和路径。uWSGI等部署工具不在核心运行依赖清单中，需在目标Linux环境另外安装。

### 1. 设置生产环境变量

```dotenv
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=替换为足够长的随机密钥
DJANGO_ALLOWED_HOSTS=ai.example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://ai.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://ai.example.com
# 只有可信代理覆盖X-Forwarded-Proto、后端不被绕过直访时才启用。
DJANGO_TRUST_PROXY=true
```

用自己的域名替换示例；允许来源带协议，ALLOWED_HOSTS不带协议。前后端分域部署时按实际前端来源填写白名单，并额外验证Cookie策略；本项目默认打包同域部署。生成密钥可在本机执行：

```powershell
& .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

把输出只保存到自己的配置中。生产DEBUGfalse会要求密钥，并启用Secure Cookie、HTTPS重定向和HSTS；未配置HTTPS前不要把本地HTTP环境直接切为生产模式。

| 部署字段 | 含义 |
|---|---|
| `DJANGO_DEBUG` | 本地true，生产false |
| `DJANGO_SECRET_KEY` | Django签名密钥，不是文字/语音API密钥；本地可用开发默认值 |
| `DJANGO_ALLOWED_HOSTS` | 允许访问的域名，以英文逗号分隔 |
| `DJANGO_CORS_ALLOWED_ORIGINS` | 允许带Cookie跨域请求的前端来源，包含协议/必要端口 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | admin等CSRF表单信任的HTTPS来源 |
| `DJANGO_TRUST_PROXY` | 默认false，仅可信反向代理时true |

### 2. 构建、迁移和收集静态资源

Linux服务器根目录：

```bash
.venv/bin/python -m pip install -r requirements-runtime.txt
cd frontend
npm ci
npm run build
cd ..
.venv/bin/python backend/manage.py migrate --noinput
.venv/bin/python backend/manage.py collectstatic --noinput
.venv/bin/python backend/manage.py check --deploy
```

### 3. 启动服务并配置代理

- WSGI负责Django；示例uWSGI监听`127.0.0.1:8000` **uwsgi协议socket**，Nginx使用`uwsgi_pass`，不能混用HTTP `proxy_pass`。示例没有指定虚拟环境，启动时需保证uWSGI使用对应Python环境，必要时配置`home`。
- 独立守护worker，命令为 `.venv/bin/python backend/manage.py run_jobs`，工作目录设为仓库根目录。
- Nginx提供 `/static/` 与公开 `/media/`；私人音频走鉴权接口，不能把private_storage映射为公共目录。
- 聊天SSE关闭代理缓冲并留够上游超时；配置实际TLS证书后先运行 `nginx -t`，通过再加载。
- 验证HTTPS登录恢复、历史语音访问、任务重启恢复、限流与备份。生产机的Nginx/证书/负载验收尚需部署环境完成。

备份应包含SQLite数据库、`media`、`private_storage`，配置密钥另外保管。SQLite使用备份API或停服务后复制；复制正在写入的文件不等于一致性备份。恢复要在隔离环境演练。
