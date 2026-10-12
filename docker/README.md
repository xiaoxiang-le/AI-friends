# Docker运行

从仓库根目录操作。需要Docker Engine或Docker Desktop的Linux容器模式，以及Compose 2.30及以上（也支持后续主版本）。构建过程需要访问Docker镜像仓库、npm和PyPI。

## 配置与启动

首次将 `backend/.env.example` 复制为 `backend/.env`，已有配置不覆盖。按根README填写所选服务的文字、语音识别和语音合成独立字段，并确认接口协议兼容。API Key只在启动时通过env_file传入，不作为构建参数；`.dockerignore`排除实际.env、数据库、上传文件和本机依赖。

本机HTTP运行保持 `DJANGO_DEBUG=true`、`DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost`、`DJANGO_TRUST_PROXY=false`。Compose覆盖 `DJANGO_DATA_DIR=/data`，不要填本机Windows路径。Compose会解析env_file中的变量，含字面量 `$` 的配置值应按Compose规则使用单引号保护，不要直接运行 `docker compose config` 并公开其展开的密钥。

```text
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=80 init web worker nginx
```

打开 http://127.0.0.1:8080/ 。默认仅绑定本机8080，不占用现有8000/5173服务。首次数据库为空，先注册账号；未配置外部API也能注册和管理角色。init应以0退出，其余三个服务保持运行并变为healthy；init失败时先查日志，其依赖服务不会正常启动。

启动顺序：init检查数据目录写权限、补齐默认头像、执行迁移并清理/重新收集静态文件 → web与worker启动 → web健康检查通过 → Nginx启动。新增 `/api/health/` 会查询账号表，确认数据库及迁移后表可访问，失败返回503且不暴露连接信息；不调用收费供应商接口、不要求用户登录。该端点单独豁免HTTPS重定向，以便容器内部HTTP探测，其余页面仍保持生产HTTPS策略。

web每15秒探测接口；worker每30秒检查PID1对应的数据库心跳，允许长任务执行5分钟；Nginx每15秒经HTTP入口检查健康接口。当前配置只运行一个worker，不要直接横向扩容SQLite方案。Docker将探测失败标记为unhealthy，**不会仅因unhealthy自动重启**；restart策略处理进程退出，卡死等情况仍需查看日志处理。日志限制为每容器最多3份、每份10MB。

## 镜像与进程

| 构建阶段/服务 | 职责 |
|---|---|
| frontend-build | Node22安装锁定依赖、准备本地VAD、构建Vue、同步Django模板 |
| python-build | Python3.12安装运行依赖及固定版本Gunicorn |
| backend / web | 默认镜像目标，以UID10001运行Gunicorn；1工作进程、4线程、180秒超时 |
| backend / init | initialize.py先验证存储写权限和头像，再执行migrate与collectstatic，成功后web/worker启动 |
| backend / worker | 同一镜像单独执行run_jobs，避免随WSGI启动多个任务循环 |
| nginx / nginx | 网关镜像，提供static/media和HTTP代理；关闭缓冲以支持SSE |

单独构建后端镜像：

```text
docker build --target backend -t ai-friends-backend:local .
```

该镜像默认仅启动Gunicorn，不会自动运行迁移、worker或提供生产静态文件；完整网站使用Compose。Gunicorn是HTTP协议，配置中使用proxy_pass，与仓库旧uWSGI配置的uwsgi_pass不同。

## 持久化、管理与更新

命名卷 `ai-friends_app-data`包含SQLite、公开media、私有private_storage及收集后的staticfiles。新卷从后端镜像继承可写目录及默认头像。Nginx只读挂载卷，仅公开static/media；私有音频继续通过Django鉴权或签名端点访问。

创建管理员：

```text
docker compose exec web python manage.py createsuperuser
```

更新代码/依赖/环境配置后，停止旧容器，再重建启动，以保证init重新执行及新路由生效：

```text
docker compose down
docker compose up --build -d
```

down保留数据卷。**不要使用down -v，除非明确要清空全部容器数据。** 不将整个本机backend目录挂载到/app/backend，否则会覆盖镜像中的构建资源、模板和代码。

已有数据库不会自动从本机导入。若迁移已有安装，先停止本机写入服务，按SQLite一致性备份方法备份数据库、media及private_storage；停止容器web/worker后，将备份导入卷内对应路径，确保UID10001可读写，再启动init迁移与收集静态资源。不得用空库覆盖旧库；恢复先在独立卷验收。不能仅复制db.sqlite3而遗漏其图片和私有语音。

## HTTPS生产部署

配套 [compose.production.yaml](../compose.production.yaml) 在同一Nginx容器终止TLS。先准备真实域名、已签发且匹配域名的证书、服务器80/443端口与防火墙规则。证书自动申请/续期不由此配置管理。

1. 在 `backend/.env` 填写强随机 `DJANGO_SECRET_KEY` 及文字/语音凭据。生产覆盖配置自动设置DEBUG=false、TRUST_PROXY=true，以及对应HTTPS域名的ALLOWED_HOSTS/CORS/CSRF。本机 `.env` 中的true不会覆盖生产Compose明确设置的false。复刻需要填写 `PUBLIC_BASE_URL=https://你的实际域名`。
2. 将 `docker/production.env.example` 复制为 `docker/production.env`，填写 `APP_DOMAIN`（仅域名，不带协议/路径）及 `TLS_CERT_DIR`（服务器绝对目录）。该目录中必须有 `fullchain.pem`、`privkey.pem`；证书私钥不提交、不打进镜像。`backend/.env`是应用配置，`docker/production.env`是Compose变量替换配置，两份文件用途不同。
3. 从项目根目录验证、构建和启动：

```text
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml config --quiet
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml build
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml run --rm --no-deps init
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml run --rm --no-deps nginx nginx -t
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml up -d
docker compose --env-file docker/production.env -f compose.yaml -f compose.production.yaml ps -a
```

首次先构建镜像并运行init，使数据卷先由后端创建，再验证Nginx配置。up阶段再次执行init也不会清空账号和私有文件。真正证书必须在目标服务器检验，config --quiet不代表证书有效。

覆盖文件使用 `ports: !override`将本机8080入口替换为80/443，不会叠加暴露旧端口。HTTP访问自动跳转HTTPS；Nginx提供TLS并覆盖转发协议头，Gunicorn不发布主机端口，因此TRUST_PROXY=true与实际拓扑匹配。内部健康检查仍通过HTTP进行。访问 `https://你的域名/`。

生产日志、管理员命令、更新与down操作也必须带相同的 `--env-file` 和两个 `-f` 参数，防止误使用本机HTTP配置。更新仍采用down（不加-v）后up --build，保证静态资源清理与迁移不和旧web/worker同时运行。

如果选择由服务器现有外层网关终止TLS，应使用另一套明确限制入口和转发头的配置，不能直接复用本模板并叠加信任浏览器头。

## 验收状态

开发电脑没有Docker Engine及可用Linux容器环境，因此没有实际运行docker build、Compose启动或nginx -t。使用单独下载且校验官方SHA256的Compose CLI检查配置；配置解析、数据路径隔离检查和Django回归不等同于镜像运行成功。

本次已验证：官方Compose CLI解析基础/生产配置成功，生产端口替换为80/443、服务依赖和探针符合预期；89项后端测试通过、无新增迁移；隔离目录连续运行两次initialize，数据库表、默认头像和静态文件建立成功，已有数据库内容及私有文件保留。原本机.env和数据库未被初始化测试覆盖。

在具备Docker环境的机器执行上述启动命令后，应验证登录、角色创建/删除、静态及VAD请求、语音文件鉴权、知识任务、文字流输出，以及down/up后的数据保留，再完成容器验收。

参考：[Docker多阶段构建](https://docs.docker.com/build/building/multi-stage/)、[Gunicorn配置](https://gunicorn.org/reference/settings/)。
