# 本地运行与服务配置（2026-10-10）

完整功能定义见[产品文档](docs/PRODUCT.md)，当前测试证据见[验收报告](docs/ACCEPTANCE.md)。

## 环境与启动

Python3.12+，Node20.19+或22.12+；核心依赖见requirements-runtime.txt，前端使用npm ci。已有.env不要再覆盖。第一次按README安装和构建，再在根目录运行：

```powershell
.\start-local.ps1
```

脚本检查8000/5173端口，执行迁移、准备本地VAD资源，启动Django、Vite与run_jobs。日志及PID在.local。前端开发地址http://127.0.0.1:5173，打包页http://127.0.0.1:8000。

手动运行三个终端：

```powershell
& .\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
& .\.venv\Scripts\python.exe backend/manage.py run_jobs
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

以上三行分别在独立终端运行；前端cd/npm同一终端。run_jobs --once会处理当前可执行任务然后退出，只用于诊断。缺少worker时知识/复刻/摘要停在排队，文本聊天仍可运行。

修改.env或构建新前端后，重启backend与worker。--noreload不自动更新Python代码，Django模板缓存也可能仍指向旧构建文件。先查看.local/pids.json，再核对进程命令行和端口归属，停止本项目的启动器及其Python子进程；不要按过期PID误停其他应用。

## DeepSeek文字与阿里云语音

backend/.env分别填写：

```dotenv
AI_API_KEY=你的DeepSeek密钥
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
AI_ENABLE_TOOLS=true
ASR_API_KEY=你的阿里云百炼密钥
ASR_WSS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/inference/
ASR_MODEL=fun-asr-realtime
TTS_API_KEY=你的阿里云百炼密钥
TTS_WSS_URL=wss://dashscope.aliyuncs.com/api-ws/v1/inference/
TTS_MODEL=cosyvoice-v3-flash
MEMORY_AUTO_UPDATE=false
ENABLE_LEGACY_KNOWLEDGE=false
```

这是北京地域示例，账号地域、接口和模型必须匹配。模型名称以账号实际可用为准；本次账号的gummy-realtime-v1返回Model not exist，fun-asr-realtime已真实通过。项目同时适配FunASR和Gummy响应结构，不能仅更换模型名而不验证协议。

AI_API_KEY/BASE_URL回退旧API_KEY/API_BASE；ASR/TTS各自凭据和WebSocket回退旧API_KEY/WSS_URL。混合供应商建议全部填独立字段，旧共享字段留空，避免把DeepSeek密钥用于语音。GET /api/capabilities/只检查配置，不表示已经真实验证。

## 语音交互

“角色语音回复”开关控制TTS。成功回复先显示语音气泡，可点击播放、右键/更多转换成原回复文字；转换不额外调用ASR。TTS失败保留全文。音频历史私有保存，通过本人JWT端点读取。

语音输入上传16kHz单声道PCM16，最长60秒；识别先确认再发送。VAD资源本地加载，识别一句后暂停采集。真实人声、设备权限与手机浏览器仍需补验。

## 知识与长期记忆

创作中心 → 知识、音色与任务 → 选择角色 → 上传UTF-8 TXT/Markdown。单文件1MB/20万字、每角色20份，完成异步索引后聊天显示来源。默认关键词检索即可使用，不依赖旧共享演示表。

可选语义检索填写EMBEDDING_API_KEY、EMBEDDING_BASE_URL、EMBEDDING_MODEL，随后上传新文件或重试失败索引。现有就绪关键词文档不会自动重建为向量索引；需要语义模式时重新导入。查询嵌入失败会回退关键词。未配置时不要填写DeepSeek聊天模型冒充嵌入模型。

聊天中的长期记忆可查看、编辑、清空、关闭，保存需要当前version。MEMORY_AUTO_UPDATE=true时每10条成功对话入库一个摘要任务，worker处理；MEMORY_MODEL可独立指定，否则回退AI_MODEL。手动清空与关闭使旧版本任务不能覆写。默认不开启自动策略。

## 个人音色复刻

还需VOICE_URL（北京示例https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization）、PUBLIC_BASE_URL（本应用公网HTTPS域名）及匹配的TTS账号模型。localhost不能让供应商抓取样本。

资源页上传有使用授权的10至20秒、单声道16位PCM WAV、至少16kHz、最多10MB，每人最多10个音色。样本保存在私有目录，以30分钟签名地址供供应商获取；成功后删除样本，失败样本留待处理。供应商提交结果不确定时需管理员核对，禁止盲目重复付费创建。

复刻就绪后才能选择。删除在用音色必须先修改引用角色；后台先云端删除后本地删除。当前未真实复刻验收。

## 管理与生产部署

创建管理员使用manage.py createsuperuser，访问/admin/。REQUIRE_CHARACTER_REVIEW=true启用公开角色审核；admin设置published/rejected并填写拒绝原因。用户举报结果显示在资源页。GET /api/admin/health/仅staff可以读取，含数据库、worker心跳、队列及AI/ASR/TTS最近实际结果。

生产按.env.example设置DJANGO_DEBUG=false、DJANGO_SECRET_KEY、ALLOWED_HOSTS、CORS/CSRF白名单。只有可信反向代理覆盖X-Forwarded-Proto时设置DJANGO_TRUST_PROXY=true。强密钥与DEBUGfalse时开启Secure Cookie、SSL重定向和HSTS。

按实际路径修改nginx.conf和scripts/uwsgi.ini：构建后collectstatic，Nginx提供static/media，聊天关闭缓冲并留够上游超时，独立守护run_jobs。禁止把private_storage目录公开映射。nginx -t与真实证书部署未在本次Windows本地验收。

数据库备份使用SQLite备份接口或停服务后复制，避免正在写入时直接复制不一致文件。备份还应包含media、private_storage，并在隔离环境验证迁移和资源恢复。配置密钥另行安全保管。

## 回归命令

```powershell
& .\.venv\Scripts\python.exe backend/manage.py check
& .\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe backend/manage.py test web --noinput
cd frontend
npm test
npm run build
```

本轮90项通过及真实服务证据见ACCEPTANCE。正式发布还需真实设备、复刻环境、Nginx、负载与生产恢复验收。
