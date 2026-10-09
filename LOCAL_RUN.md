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
