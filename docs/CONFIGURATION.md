# 环境配置与服务接入

[返回项目首页](../README.md) · [Docker部署](DEPLOYMENT.md) · [本地开发](DEVELOPMENT.md)

所有应用配置写在 `backend/.env`，模板为 `backend/.env.example`。已有文件不覆盖，API密钥只由后端读取。Docker所需域名和证书部署变量另见部署指南。

## 配置 backend/.env

### 1. 最少需要配置什么

- 只浏览页面、注册登录、管理角色：不需要外部 API；保留开发环境配置，先执行迁移。
- 启用文字聊天：填写所选 OpenAI 兼容服务的 `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`，不限于 DeepSeek。
- 启用语音输入：额外填写 `ASR_API_KEY`、`ASR_WSS_URL`，使用账号可用的 `ASR_MODEL`。
- 启用角色语音回复：额外填写 `TTS_API_KEY`、`TTS_WSS_URL`，使用匹配音色的 `TTS_MODEL`。
- 个人音色复刻、语义检索、自动记忆：按[启用可选功能](#启用可选功能)配置。它们不阻塞基础文字聊天。

**第一次只运行文字聊天时**，在刚复制的 `backend/.env` 中找到下面三行，按所选供应商填写，其他字段先保留模板默认值。不要在文件末尾重复添加同名字段。

```dotenv
AI_API_KEY=你的文字服务API_Key
AI_BASE_URL=供应商提供的OpenAI兼容基础地址
AI_MODEL=该服务实际支持的模型名称
```

模型名称需以所选服务实际支持的名称为准。如果暂时没有 API Key，可以将这三项留空，先验证页面、注册登录和角色管理；此时无法获得 AI 回复。保存文件后返回[本地开发指南](DEVELOPMENT.md#5-初始化数据库并构建页面)的第5步。

### 2. 通用 API 接入配置

在 `backend/.env` 中填写你选择的模型服务配置。以下字段不指定供应商、接口地址或模型名称，均由你根据服务商文档填写；文字聊天、语音识别和语音合成分别配置。**占位文字必须替换为真实配置；未启用的语音和可选服务字段留空，不要把占位文字作为配置值保存。** 文字接口需兼容 OpenAI 聊天协议，语音接口需兼容当前后端的 DashScope WebSocket 任务协议；其他协议需要增加适配代码。

```dotenv
# 旧版共享字段：混合供应商时保持为空，使用下方各服务独立字段。
API_KEY=
API_BASE=
WSS_URL=

# 文字聊天：填写所选服务的配置。
# AI_BASE_URL 是OpenAI兼容基础地址，不是 /chat/completions 完整路径。
AI_API_KEY=你的文字服务API_Key
AI_BASE_URL=你的文字服务OpenAI兼容基础地址
AI_MODEL=你的文字模型名称
# 模型不支持工具调用时设为false。
AI_ENABLE_TOOLS=true

# 语音识别：启用时填写；密钥、地域、接口和模型必须匹配。
# WebSocket接口需兼容当前DashScope任务协议。
ASR_API_KEY=你的语音识别服务API_Key
ASR_WSS_URL=你的语音识别WebSocket接口地址
ASR_MODEL=你的语音识别模型名称

# 语音合成：启用时填写；模型需与角色选择的音色匹配。
# WebSocket接口需兼容当前DashScope任务协议。
TTS_API_KEY=你的语音合成服务API_Key
TTS_WSS_URL=你的语音合成WebSocket接口地址
TTS_MODEL=你的语音合成模型名称

# 长期记忆：手动记忆可用；自动摘要默认关闭。
MEMORY_MODEL=
MEMORY_AUTO_UPDATE=false
ENABLE_LEGACY_KNOWLEDGE=false

# 个人音色复刻：未启用时留空；不影响预设音色使用。
VOICE_URL=
PUBLIC_BASE_URL=

# 可选嵌入服务：全部留空时，角色知识库使用本地关键词检索。
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=

# 本地HTTP开发配置。
DJANGO_DATA_DIR=
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
DJANGO_CSRF_TRUSTED_ORIGINS=
DJANGO_TRUST_PROXY=false

# 公开角色是否必须先由管理员审核。
REQUIRE_CHARACTER_REVIEW=false
```

`.env` 中一行一个 `名称=值`，布尔开关使用小写 `true` / `false`。操作系统已设置的同名环境变量优先于文件，因为当前 `load_dotenv` 不覆盖已有变量。修改后必须重启 Django 后端和 `run_jobs`，刷新浏览器不足以加载新配置。

### 3. 密钥、模型和接口从哪里获取

从所选服务商的控制台和官方接入文档获取以下信息：

| 服务 | 需要获取的信息 | 填写字段 |
|---|---|---|
| 文字聊天 | API Key、OpenAI 兼容基础地址、可调用的聊天模型名称 | `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL` |
| 语音识别 | API Key、兼容当前任务协议的 WebSocket 地址、识别模型名称 | `ASR_API_KEY`、`ASR_WSS_URL`、`ASR_MODEL` |
| 语音合成 | API Key、兼容当前任务协议的 WebSocket 地址、合成模型名称及匹配音色 | `TTS_API_KEY`、`TTS_WSS_URL`、`TTS_MODEL` |

**文字模型接入**：后端通过 `ChatOpenAI` 调用服务，接口需兼容 OpenAI 聊天请求与流式输出。更换服务时一起修改文字服务的三个字段，模型名称必须是该账号实际可调用的名称。不支持工具调用的模型设置 `AI_ENABLE_TOOLS=false`。非 OpenAI 兼容接口需要增加后端适配。

**语音服务接入**：按服务商文档核对密钥所属账号、业务空间、地域、接口地址及模型权限。当前后端采用 DashScope WebSocket 任务协议；协议不同的服务需要适配请求、音频传输和响应处理，不能仅更换地址。语音合成还需确保角色音色与模型兼容。

配置完成后重启 Django 后端和 `run_jobs`，先发送文字消息验证 AI 回复，再按需测试音色试听和录音识别。文字、ASR 和 TTS 的密钥分别属于对应服务，不要混用；未启用语音时可只配置文字服务。

### 4. 字段说明与回退关系

| 字段 | 必填条件 | 内容/默认行为 |
|---|---|---|
| `API_KEY` / `API_BASE` / `WSS_URL` | 仅旧版共享配置使用 | 混合供应商留空；不要同时填互相冲突的密钥 |
| `AI_API_KEY` | 文字聊天 | 文字服务密钥；为空回退 `API_KEY` |
| `AI_BASE_URL` | 文字聊天 | OpenAI兼容基础地址；为空回退 `API_BASE` |
| `AI_MODEL` | 文字聊天 | 账号实际可用模型；无自动默认模型 |
| `AI_ENABLE_TOOLS` | 可保留默认 | 默认true；false不绑定时间等工具 |
| `ASR_API_KEY` / `ASR_WSS_URL` | 语音识别 | 分别回退 `API_KEY` / `WSS_URL` |
| `ASR_MODEL` | 可保留默认 | 默认fun-asr-realtime；按账号模型与协议验证 |
| `TTS_API_KEY` / `TTS_WSS_URL` | 语音回复或试听 | 分别回退 `API_KEY` / `WSS_URL` |
| `TTS_MODEL` | 可保留默认 | 默认cosyvoice-v3-flash；音色必须匹配模型 |
| `MEMORY_MODEL` | 可选 | 留空复用AI_MODEL及文字服务凭据 |
| `MEMORY_AUTO_UPDATE` | 可选 | 默认false；true才安排自动摘要任务 |
| `ENABLE_LEGACY_KNOWLEDGE` | 保留false | 老共享演示表，不是角色知识文件功能的开关 |
| `VOICE_URL` | 个人音色复刻 | 供应商HTTP复刻接口完整地址，必须HTTPS |
| `PUBLIC_BASE_URL` | 个人音色复刻 | 本应用公网HTTPS根地址，供供应商下载限时样本 |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | 可选语义检索 | 三项一起配置；不回退文字服务字段 |
| `REQUIRE_CHARACTER_REVIEW` | 可选 | 默认false；true开启公开角色先审后发 |

## 数据库、文件和前后端地址

**数据库**：默认使用 `backend/db.sqlite3`；设置可选的 `DJANGO_DATA_DIR` 后使用该目录下的 `db.sqlite3`，Compose自动设为 `/data`。不需要配置 `DB_HOST`、MySQL密码或启动数据库服务器；不存在自动读取数据库连接字符串的配置。如果要换PostgreSQL/MySQL，需修改Django数据库配置、安装驱动并单独迁移验收。

| 路径 | 内容 | 是否随Git提交 |
|---|---|---|
| `backend/.env` | 本机供应商与部署配置 | 否 |
| `backend/db.sqlite3` | 用户、角色、聊天、知识、任务等 | 否 |
| `backend/media` | 用户头像与角色图片 | 用户上传不提交，仓库保留默认头像 |
| `backend/private_storage` | 私人聊天语音和复刻样本 | 否；不通过公共media直接提供 |
| `backend/static/frontend` | 前端build生成页面、JS/CSS/VAD资源 | 否，由build生成 |
| `backend/staticfiles` | collectstatic生成的生产静态资源 | 否 |
| `.local` | 一键启动日志和PID | 否 |

**前端连接地址**在 `frontend/src/js/config/config.js`：开发时连接 `http://127.0.0.1:8000`，打包后使用页面当前域名。当前没有实现 `VITE_API_BASE_URL` 配置，向前端 `.env` 随意添加该字段不会改地址。

本地统一使用 `127.0.0.1` 访问前后端，避免`localhost`与IP混用导致Cookie登录恢复异常。如果改后端端口/域名，同步检查该前端配置、后端CORS/CSRF白名单及启动命令；若改开发端口，同步修改CORS允许的前端来源。默认开发服务仅绑定本机地址。

## 启用可选功能

### 角色知识与可选语义检索

在“创作中心 → 知识、音色与任务”选择角色，上传UTF-8 TXT/Markdown，等待任务完成。每角色最多20份，每份最多1MB/20万字符。默认关键词方案无需另外购买或配置嵌入服务。

需要语义检索时，填写全部 `EMBEDDING_*` 字段：密钥、OpenAI兼容嵌入基础地址、实际嵌入模型。该接口必须支持embeddings，不要填只提供聊天的模型。重启worker后重新导入需要向量化的文档；旧就绪关键词文档不会自动重建。

### 自动长期记忆

手动记忆可直接使用。需要自动摘要时设 `MEMORY_AUTO_UPDATE=true` 并运行worker；每10条成功对话安排摘要。`MEMORY_MODEL`空值复用文字模型，不需要独立摘要密钥。会话中关闭记忆后不读取/更新，手动保存和清空有版本保护。

### 个人音色复刻

预设音色只需要TTS配置。创建自己的音色额外需要：

```dotenv
# 北京业务空间示例；WorkspaceId替换为自己的真实业务空间ID。
VOICE_URL=https://你的WorkspaceId.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/customization
# 替换为本应用已部署、供应商能够访问的公网HTTPS域名。
PUBLIC_BASE_URL=https://你的应用域名
```

`VOICE_URL`是阿里云复刻服务地址，`PUBLIC_BASE_URL`是你的网站地址，两者用途不同。后者不能填DeepSeek地址或localhost；供应商需要下载本应用生成的限时样本URL。本项目旧北京HTTP复刻地址示例为 `https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization`，新接入按[官方声音复刻文档](https://help.aliyun.com/zh/model-studio/voice-cloning-user-guide)匹配账号地域、目标模型与地址。

在资源页提交拥有使用授权的10至20秒、单声道、16位PCM、至少16kHz、最多10MB的WAV样本，运行worker处理。成功音色才能在角色编辑中选择；被角色引用时不能直接删除。提交结果不确定的失败需管理员核对云端资源后处理，不要反复创建。

### 公开角色审核

`REQUIRE_CHARACTER_REVIEW=true`开启公开角色先审后发。管理员通过 `/admin/` 将角色状态设为published或rejected并填写拒绝原因；作者可查看结果。默认false时沿用直接发布流程。
