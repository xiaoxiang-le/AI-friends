# AIFriends 
> 一个大模型应用入门项目，支持用户创建并分享虚拟角色，实现语音交互和智能对话

## 项目地址：https://app7804.acapp.acwing.com.cn/
<img width="2559" height="1452" alt="image" src="https://github.com/user-attachments/assets/5aea2de6-edbe-4649-adff-0104b3580a96" />

## 📖 项目简介

AIFriends 是一个基于大语言模型的虚拟角色创作分享平台。用户可以创建任意多个虚拟女友/男友/朋友，自定义角色音色、性格、简介，并通过语音识别、语音合成、语音复刻等技术实现与虚拟人物的语音通话交流。

本项目采用前后端分离架构，后端使用 Django，前端使用 Vue3，大模型框架采用 LangChain。

## ✨ 功能特性

- 🎭 **角色创建与管理**：支持创建并分享任意多个虚拟角色，可自定义音色、性格、简介
- 🎤 **语音交互**：支持语音识别、语音合成、语音复刻，实现与虚拟人物语音通话交流
- 🤖 **智能对话**：基于大语言模型的智能对话系统
- 🔧 **Function Call**：支持函数调用功能
- 📚 **知识库**：支持知识库功能
- 🔐 **用户认证**：基于 JWT 的用户认证系统
- 🌐 **跨域支持**：配置了 CORS 跨域资源共享

## 🛠️ 技术栈

### 后端
- **框架**：Django 6.0.1
- **认证**：Django REST Framework + Simple JWT
- **大模型框架**：LangChain
- **数据库**：SQLite（开发环境）
- **跨域**：django-cors-headers

### 前端
- **框架**：Vue 3.5.26
- **构建工具**：Vite 7.3.0
- **路由**：Vue Router 4.6.4
- **状态管理**：Pinia 3.0.4

## 📁 项目结构

```
AIFriends/
├── backend/                 # Django 后端项目
│   ├── backend/             # Django 项目配置
│   │   ├── settings.py      # 项目设置
│   │   ├── urls.py          # 主 URL 配置
│   │   └── wsgi.py          # WSGI 入口
│   ├── web/                 # Web 应用
│   │   ├── views/           # 视图（含 user/account 登录注册等）
│   │   ├── templates/       # 模板（index.html 为前端入口）
│   │   ├── urls.py          # URL 路由
│   │   └── models/          # 数据模型（如 UserProfile）
│   ├── static/              # 静态文件（Vite 构建输出到此）
│   │   └── frontend/        # 前端构建产物
│   ├── staticfiles/        # collectstatic 收集目录（生产）
│   ├── media/               # 用户上传文件（如头像）
│   ├── manage.py
│   └── db.sqlite3
├── frontend/                # Vue3 前端项目
│   ├── src/
│   │   ├── components/     # 组件（NavBar、UserMenu 等）
│   │   ├── views/           # 页面（首页、登录、注册等）
│   │   ├── router/          # 路由与守卫
│   │   ├── stores/          # Pinia（user 等）
│   │   └── js/http/         # axios 封装（api.js）
│   ├── package.json         # 含 postbuild：同步 Django 模板
│   └── vite.config.js       # 构建输出到 backend/static/frontend
├── scripts/                 # 部署与构建脚本
│   ├── uwsgi.ini            # uWSGI 配置
│   └── update-django-static.js  # 构建后更新 Django 模板中的静态路径
├── nginx.conf               # Nginx 配置示例
├── deploy-frontend.ps1      # 前端构建与部署脚本（Windows）
└── README.md
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 20.19.0+ 或 22.12.0+
- npm 或 yarn

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd AIFriends
```

#### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install django==6.0.1
pip install djangorestframework
pip install djangorestframework-simplejwt
pip install django-cors-headers
pip install langchain
# 根据实际需求安装其他依赖

# 运行数据库迁移
python manage.py migrate

# 创建超级用户（可选）
python manage.py createsuperuser
```

#### 3. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 构建前端项目（生产环境）
# 构建产物输出到 backend/static/frontend/，并自动更新 backend/web/templates/index.html 中的静态路径
npm run build
```

#### 4. 运行项目

**开发模式：**

```bash
# 终端1：启动后端服务
cd backend
python manage.py runserver

# 终端2：启动前端开发服务器
cd frontend
npm run dev
```

**生产模式：**

```bash
# 只需启动后端服务，前端已构建到 static 目录
cd backend
python manage.py runserver
```

访问 `http://127.0.0.1:8000/` 即可查看应用。

## ⚙️ 配置说明

### 后端配置

主要配置文件：`backend/backend/settings.py`

- **静态文件配置**：
  - `STATIC_URL = 'static/'`
  - `STATIC_ROOT = BASE_DIR / 'staticfiles'`（生产环境 collectstatic 目标）
  - `STATICFILES_DIRS = [BASE_DIR / 'static']`（开发时前端构建产物在 static/frontend）

- **跨域配置**：
  - `CORS_ALLOWED_ORIGINS`：允许的前端域名
  - 默认允许 `http://localhost:5173`（Vite 开发服务器）

- **JWT 配置**：
  - Access Token 有效期：2 小时
  - Refresh Token 有效期：7 天

### 前端配置

主要配置文件：`frontend/vite.config.js`

- 开发服务器端口：5173
- 构建输出目录：`../backend/static/frontend`（与 Django 静态目录一致）
- `npm run build` 后会自动执行 `scripts/update-django-static.js`，同步 Django 模板中的 js/css 路径

## 📡 API 接口

### 用户认证

- `POST /api/user/account/login/` - 登录（返回 access，cookie 设置 refresh_token）
- `POST /api/user/account/register/` - 注册
- `POST /api/user/account/logout/` - 退出（需登录，删除 refresh_token cookie）
- `POST /api/user/account/refresh_token/` - 使用 cookie 中的 refresh_token 刷新 access
- `GET /api/user/account/get_user_info/` - 获取当前用户信息（需登录）

### 页面与静态

- `GET /` 及前端路由 - 返回前端 SPA 入口，由 Vue Router 接管
- `/static/`、`/media/` - 静态与媒体文件

## 🔧 开发说明

### 前端开发

前端使用 Vue3 + Vite 开发，支持热重载：

```bash
cd frontend
npm run dev
```

开发完成后执行 `npm run build`，构建产物会输出到 `backend/static/frontend/`，并自动更新 `backend/web/templates/index.html` 中的静态引用。

### 后端开发

后端使用 Django 开发，支持自动重载：

```bash
cd backend
python manage.py runserver
```

### 静态文件加载

项目使用 Django 的静态文件系统，模板中使用 `{% load static %}` 和 `{% static %}` 标签加载静态资源。

## 🚢 部署概要

1. **克隆**：`git clone <repo>`，进入项目目录
2. **后端**：`cd backend` → 虚拟环境、`pip install` 依赖、`python manage.py migrate`、`python manage.py collectstatic --noinput`
3. **前端**：`cd frontend` → `npm install`、`npm run build`（会输出到 `backend/static/frontend/` 并更新 Django 模板）
4. **运行**：使用 `scripts/uwsgi.ini` 启动 uWSGI（需先按服务器路径修改 `chdir` 等），Nginx 参考 `nginx.conf` 配置反向代理与静态/媒体路径；`ALLOWED_HOSTS` 需包含域名与服务器 IP

## 📝 注意事项

1. **开发环境**：当前配置为开发环境（`DEBUG = True`），生产环境需设置 `DEBUG = False`、`ALLOWED_HOSTS`
2. **数据库**：开发环境使用 SQLite，生产环境建议使用 PostgreSQL 或 MySQL
3. **静态文件**：生产环境使用 Nginx 提供 `/static`、`/media`，Django 端执行 `python manage.py collectstatic`
4. **密钥安全**：生产环境务必修改 `SECRET_KEY` 并妥善保管
5. **部署**：项目内提供 `nginx.conf`、`scripts/uwsgi.ini` 示例，部署时按实际路径修改后使用

## 📚 相关资源

- [Django 官方文档](https://docs.djangoproject.com/)
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [LangChain 文档](https://python.langchain.com/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**注意**：本项目为课程项目，更多信息请参考课程页面。
