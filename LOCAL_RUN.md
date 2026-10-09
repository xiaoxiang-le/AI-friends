# 本地运行

在项目根目录执行：

```powershell
.\start-local.ps1
```

前端：http://127.0.0.1:5173

后端及打包后的页面：http://127.0.0.1:8000

日志存放在 `.local`，启动的进程号记录在 `.local/pids.json`。启动脚本要求 8000 和 5173 端口空闲。

停止本次启动的服务（请先确认记录的进程号仍属于本项目）：

```powershell
Get-Content .local/pids.json
Get-Process -Id <进程号>
Stop-Process -Id <进程号>
```

Python 依赖安装在项目的 `.venv` 中，前端依赖安装在 `frontend/node_modules` 中。前端开发模式连接本地 Django，构建模式也连接本地 Django。

AI 对话、语音识别和语音合成需要把 `backend/.env.example` 复制为 `backend/.env`，填写服务商提供的 `API_KEY`、`API_BASE` 和 `WSS_URL` 后重新启动后端。知识库检索还需要导入知识库，音色和系统提示词需要按课程配置。
# AI、语音与记忆配置（2026-10-09）

在 `backend/.env` 中配置服务，完整字段见 `backend/.env.example`。密钥不要提交到版本库。

- 文字聊天需要 `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`。前两项兼容旧字段 `API_KEY`、`API_BASE`；模型必须填写账号实际可用的模型名称。
- 不支持工具调用的 OpenAI 兼容服务可设置 `AI_ENABLE_TOOLS=false`。
- ASR 与 TTS 可分别设置 `ASR_API_KEY` / `ASR_WSS_URL` / `ASR_MODEL` 和 `TTS_API_KEY` / `TTS_WSS_URL` / `TTS_MODEL`。兼容旧的共享 `API_KEY`、`WSS_URL`。当前语音适配实现的是 DashScope 风格 WebSocket 协议，不代表所有语音供应商通用。
- 修改 `.env` 后重启 Django。`GET /api/capabilities/` 只报告是否配置完整，不报告已经真实验收，也不会返回密钥。
- 聊天默认只生成文字；勾选“语音播报”才调用 TTS。TTS 在文字生成后开始，失败会提示并保留完整文字。
- 录音识别结果先展示给用户确认，再转入文字输入框；确认后点击发送。上传格式为16kHz、单声道、小端PCM16，最长60秒。
- 长期记忆在聊天弹窗中查看、编辑或清空。清空内容后需点击保存。版本冲突时重新加载，避免覆盖其他编辑。
- 自动记忆摘要默认关闭；设置 `MEMORY_AUTO_UPDATE=true` 后每10条成功对话触发后台摘要，可用 `MEMORY_MODEL` 单独指定模型。当前后台线程不是持久化任务队列，进程重启会丢失未完成的摘要任务。
- 共享演示知识表默认关闭；正式知识库管理、按角色隔离和引用追踪仍需后续实现。不要把打开 `ENABLE_LEGACY_KNOWLEDGE` 当作知识库产品验收完成。

本次数据库迁移 `0009` 增加记忆版本和聊天请求编号，取消消息正文截断。执行：

```powershell
& .venv/Scripts/python.exe backend/manage.py migrate
& .venv/Scripts/python.exe backend/manage.py test web
cd frontend
npm test
npm run build
```

停止生成和同会话并发控制当前使用进程内登记，适合本地单进程服务。部署多个 worker 前需改用共享任务注册和取消通道；已完成请求的去重由数据库唯一约束保证。失败、停止的部分回复不保存为成功历史，前端会明确标记。

真实验收至少包含：真实模型多轮回复及全文历史、真实麦克风识别、实际音色播报、拒绝麦克风权限、服务超时、语音失败保留文字、生成中停止。测试替身和协议回归不替代这些真实验收。
