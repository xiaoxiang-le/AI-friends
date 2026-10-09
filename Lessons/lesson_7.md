# Lesson 7：项目上线与语音复刻

---

## 上节课的补丁

- **聊天框用 ESC 关闭时，也要执行关闭逻辑**：
  - 仅点击右上角关闭按钮时，`InputField.close()` 会被调用（停止音频、收起麦克风）。
  - 仅按 ESC 时，浏览器默认会关闭 `<dialog>`，但不会自动调用你的按钮事件。
  - 处理方式：在 `ChatField.vue` 的 `<dialog>` 上绑定 `@close="handleClose"`（或同等回调），确保 ESC 与点击关闭按钮行为一致。

---

## 1. 配置云服务器

### 1.1 租云服务器

- 云厂商可用阿里云：[https://www.aliyun.com/](https://www.aliyun.com/)
- 安全组至少放行：
  - `22`（SSH）
  - `80`（HTTP）
  - `443`（HTTPS）

### 1.2 配置免密登录

1) 先用 root 登录服务器，创建普通用户并赋权：

```bash
adduser <YOUR_SSH_USER>
usermod -aG sudo <YOUR_SSH_USER>
```

2) 本地 `~/.ssh/config` 配置（示例）：

```ssh-config
Host <YOUR_SSH_HOST_ALIAS>
    HostName <YOUR_SERVER_IP>
    User <YOUR_SSH_USER>
```

3) 推送本地公钥：

```bash
ssh-copy-id <YOUR_SSH_HOST_ALIAS>
```

4) 上传个性化配置（可选）：
- `.vimrc`
- `.tmux.conf`

### 1.3 安装 tmux

```bash
sudo apt-get update
sudo apt-get install -y tmux
```

### 1.4 安装 Python 3.14

下载 Python 3.14 源码（`XZ compressed source tarball`），上传到服务器后编译安装：

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
libffi-dev uuid-dev

tar -xvf Python-3.14.x.tar.xz
cd Python-3.14.x
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall
```

> 注意：`langchain-core` 在 Python 3.14 下会出现 pydantic v1 兼容性警告，通常不影响启动，但若后续出现链路异常，优先考虑改到 Python 3.11/3.12。

本地导出依赖后上传：

```bash
# 在 AIFriends 根目录
pip freeze > requirements.txt
```

服务器安装：

```bash
pip3.14 install -r requirements.txt --user
```

重新登录一次，让 `~/.local/bin` 自动加入 `PATH`。

---

## 2. 将本地项目部署到云端

### 2.1 绑定域名

- 在应用平台创建应用并绑定公网 IP（示例：`<YOUR_SERVER_IP>`）。
- 你的域名（示例）：`https://<YOUR_DOMAIN>`

### 2.2 上传项目

你现在使用的命令可直接用：

```bash
scp -r backend <YOUR_SSH_HOST_ALIAS>:
```

建议同时上传前端源码（如果服务器要本地构建）：

```bash
scp -r frontend <YOUR_SSH_HOST_ALIAS>:
```

### 2.3 上线前常量配置

#### 2.3.1 后端 `settings.py`

在 `AIFriends/backend/backend/settings.py` 确保至少包含：

- `ALLOWED_HOSTS`：`127.0.0.1`、`localhost`、`<YOUR_SERVER_IP>`、`<YOUR_DOMAIN>`
- `DEBUG = False`（生产环境）
- `STATIC_URL = '/static/'`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`
- `MEDIA_URL = '/media/'`
- `MEDIA_ROOT = BASE_DIR / 'media'`
- `CORS_ALLOWED_ORIGINS` 包含：
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
  - `https://<YOUR_DOMAIN>`

> 关键：`STATIC_URL` 必须是绝对路径 `/static/`。  
> 若误写成 `static/`，Django admin 会出现样式丢失（静态资源 404）。

#### 2.3.2 前端配置 `config.js`

文件：`AIFriends/frontend/src/js/config/config.js`

建议通过平台常量切换（已按该思路改造）：

```js
const platform = 'cloud' // vue / django / cloud
```

并保证 cloud 下：

```js
CONFIG_API.HTTP_URL = 'https://<YOUR_DOMAIN>'
CONFIG_API.VAD_URL = 'https://<YOUR_DOMAIN>/static/frontend/vad/'
```

### 2.4 构建前端到后端

在 `frontend` 下：

```bash
npm run build
```

当前项目已配置 `postbuild`，会自动更新 `backend/web/templates/index.html` 的静态资源哈希路径。

---

## 3. 部署服务（Gunicorn + Nginx）

### 3.1 安装部署工具

```bash
sudo apt update
sudo apt install -y nginx
pip3.14 install gunicorn --upgrade --user
```

### 3.2 Django 生产配置

```python
# backend/settings.py
DEBUG = False
```

收集静态资源：

```bash
python3.14 manage.py collectstatic
```

### 3.3 启动 Gunicorn

在 `/home/<YOUR_SSH_USER>/backend/`（项目后端目录）运行：

```bash
gunicorn --workers 3 --graceful-timeout 3 \
  --bind unix:/home/<YOUR_SSH_USER>/backend/gunicorn.sock backend.wsgi:application
```

### 3.4 配置 Nginx 反向代理

证书路径示例：

- `/etc/nginx/cert/<YOUR_CERT>.pem`
- `/etc/nginx/cert/<YOUR_CERT>.key`

在 `/etc/nginx/mime.types` 里给 `mjs` 补类型：

```nginx
application/javascript      js mjs;
```

`/etc/nginx/nginx.conf` 关键 server 示例（替换为你的域名）：

```nginx
server {
    listen 80;
    server_name <YOUR_DOMAIN>;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name <YOUR_DOMAIN>;

    ssl_certificate     /etc/nginx/cert/<YOUR_CERT>.pem;
    ssl_certificate_key /etc/nginx/cert/<YOUR_CERT>.key;

    location /static/ {
        alias /home/<YOUR_SSH_USER>/backend/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/<YOUR_SSH_USER>/backend/media/;
        expires 30d;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/home/<YOUR_SSH_USER>/backend/gunicorn.sock;
    }
}
```

重载 Nginx：

```bash
sudo nginx -s reload
```

---

## 4. 实现语音复刻（音色库）

### 4.1 音色数据库

文件：`AIFriends/backend/web/models/character.py`

已对齐为：

- `Voice`：`name`、`voice_id`、`create_time`
- `Character.voice`：外键，可空

并已提供迁移：

- `backend/web/migrations/0007_voice_and_systemprompt_align.py`

### 4.2 后端接口改造

#### 已完成

- `chat.py` 使用角色音色：
  - `voice_id = friend.character.voice.voice_id`
  - 若角色未设置音色，回退默认 `longanyang`
- `create/character/voice/get_list.py`：
  - 返回可选音色列表
- `urls.py`：
  - `api/create/character/voice/get_list/`
- `create/character/get_single.py`：
  - 编辑角色时返回 `voices` 与 `character.voice_id`
- `create/character/create.py`：
  - 创建角色时接收 `voice_id` 并写入 `Character.voice`
- `create/character/update.py`：
  - 更新角色时支持修改 `voice_id`
- `admin.py`：
  - 已注册 `Voice` 到 Django Admin
  - `CharacterAdmin.raw_id_fields` 包含 `voice`

### 4.3 前端角色创建页改造

已完成并对齐 demo：

- `frontend/src/views/create/character/components/Voice.vue`
- `CreateCharacter.vue`
- `UpdateCharacter.vue`

目标：

- 拉取 `/api/create/character/voice/get_list/`
- 用户可选择音色
- 创建/更新角色时提交音色字段

### 4.4 语音复刻 API（本地执行，云端 URL）

参考阿里云文档：
- [CosyVoice Clone Design API](https://help.aliyun.com/zh/model-studio/cosyvoice-clone-design-api)

建议在：

`AIFriends/backend/web/views/create/character/voice/custom/`

新增：

- `create_voice.py`
- `delete_voice.py`
- `list_voice.py`

并把复刻后的 `voice_id` 持久化到 `Voice` 表。

#### 4.4.1 关键参数与易错点

- `create_voice` 请求体必须是：
  - `"action": "create_voice"`（不是 `"audio": "create_voice"`）
- `delete_voice` 请求体：
  - `"action": "delete_voice"`
  - `"voice_id": "xxx"`
- `prefix` 建议使用英文数字下划线（如 `v001`），避免中文前缀带来的参数风险。

#### 4.4.2 批量获取 voice_id（本地 shell，使用云端 mp3 URL）

```python
from web.views.create.character.voice.custom.create_voice import create_voice
from web.models.character import Voice

base = "https://<YOUR_DOMAIN>/media/tmp"
for i in [1, 2, 3, 4]:
    prefix = f"v{i:03d}"
    url = f"{base}/{i}.mp3"
    res = create_voice(url, prefix)
    voice_id = (res.get("output") or {}).get("voice_id") or res.get("voice_id")
    if not voice_id:
        print("FAIL", i, res)
        continue
    obj, _ = Voice.objects.update_or_create(
        name=str(i),
        defaults={"voice_id": voice_id}
    )
    print("OK", obj.id, obj.name, obj.voice_id)
```

> 注意：云端有 mp3 文件 ≠ 数据库里自动有 `voice_id`。  
> 必须调用复刻接口后，再写入 `Voice` 表。

#### 4.4.3 本地库 vs 云端库

- 在本地 `manage.py shell` 写入的是本地数据库。
- 线上应用读取的是云服务器数据库。
- 若线上要生效，需要在云端执行同样入库，或通过线上 admin 手动录入 `voice_id`。

### 4.5 本节真实故障与修复

- 注册失败但后端只有 `OPTIONS`：
  - 原因：跨域来源不全
  - 修复：补齐 `CORS_ALLOWED_ORIGINS`
- 线上注册请求打到 `127.0.0.1:8000`：
  - 原因：`config.js` 平台未切 `cloud`
  - 修复：上线前改 `platform = 'cloud'` 并重建前端
- VAD 从 `localhost:5173` 拉模型失败：
  - 原因：线上包仍是 dev 配置
  - 修复：cloud 下 `VAD_URL = https://域名/static/frontend/vad/`
- admin 页面样式丢失：
  - 原因：`STATIC_URL` 写成相对路径 `static/`，且 Nginx 未指向 `staticfiles`
  - 修复：`STATIC_URL='/static/'` + Nginx `location /static/ -> staticfiles`
- `invalid action`：
  - 原因：请求体 action 字段错误或旧模块未重载
  - 修复：改为 `"action": "create_voice"` 并在 shell 中 reload 后重试

---

## 5. 项目更新到云端

每次发布流程建议固定为：

1. 本地切到 cloud 配置（前后端常量）
2. `npm run build`
3. 上传 `backend`（以及必要脚本/配置）到服务器
4. 服务器执行：
   - `pip3.14 install -r requirements.txt --user`（如依赖变化）
   - `python3.14 manage.py migrate`
   - `python3.14 manage.py collectstatic`
5. 重启 Gunicorn / reload Nginx
6. 打开域名回归验证：
   - 登录、聊天、SSE、语音输入、语音播报

---

## 小结

- 本节核心是把本地可跑的项目，拆成“**配置、构建、部署、回归**”四步流程。
- `Gunicorn + Nginx + HTTPS + static/media` 是 Django 上线标准组合。
- 语音模块上线时，要同时关注：
  - ASR websocket 配置（`WSS_URL`）
  - TTS 音色配置（`voice_id`）
  - VAD 静态资源路径（`VAD_URL`）
- 安全提示：文档中不要硬编码真实域名、IP、账号、证书文件名，建议统一使用占位符。

