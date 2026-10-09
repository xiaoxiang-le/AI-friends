# Lesson 1: 配置环境、创建导航栏

## 1. 配置开发环境

### 1.1 配置 PyCharm

#### 1.1.1 下载和安装
- 下载地址：https://www.jetbrains.com/zh-cn/pycharm/
- 安装时全选默认选项即可

#### 1.1.2 设置中文界面
设置路径：
- `Settings → Plugins → Marketplace`
- 搜索：`Chinese (Simplified) Language Pack`
- 安装并重启 PyCharm

#### 1.1.3 配置 Django 支持
1. 打开项目后，进入 `Settings → Languages & Frameworks → Django`
2. 勾选 `Enable Django support`
3. 设置 `Django project root` 为 `AIFriends/backend`
4. 设置 `Settings` 为 `backend/settings.py`
5. 设置 `Manage script` 为 `manage.py`

#### 1.1.4 标记源代码根目录
**重要**：为了避免 PyCharm 无法识别 `web` 模块，需要将 `backend` 目录标记为源代码根：
- 在项目树中右键 `backend` 目录
- 选择 `Mark Directory as → Sources Root`

这样 PyCharm 就能正确解析 `from web.models.user import UserProfile` 等导入语句。

### 1.2 配置 Git 环境

#### 1.2.1 安装 Git
- Windows: https://gitforwindows.org/
- Mac/Linux: 系统自带或使用包管理器安装

#### 1.2.2 注册 Git 账号
- AC Git: https://git.acwing.com/
- GitHub: https://github.com/

#### 1.2.3 生成 SSH 密钥
```bash
ssh-keygen
# 一路回车使用默认配置
```

#### 1.2.4 上传 SSH 公钥
将 `~/.ssh/id_rsa.pub` 的内容复制到 Git 网站的个人设置中。

### 1.3 安装 Node.js
- 下载地址：https://nodejs.org/en/download
- 下载 Windows Install (.msi) 并安装
- 安装时勾选 "Add to PATH"
- 更新 npm：`npm install -g npm@latest`

## 2. 创建项目

### 2.1 创建项目目录
```bash
mkdir AIFriends
cd AIFriends
```

**注意**：项目路径不能包含中文，否则后续导入 `rest_framework` 时会报错。

### 2.2 创建 Python 虚拟环境
```bash
python -m venv .venv

# Windows 激活
.venv\Scripts\activate

# Linux/Mac 激活
source .venv/bin/activate
```

### 2.3 创建后端

#### 2.3.1 安装依赖
```bash
pip install django==6.0.1
pip install djangorestframework
pip install djangorestframework-simplejwt
pip install django-cors-headers
```

#### 2.3.2 创建 Django 项目
```bash
django-admin startproject backend
cd backend
django-admin startapp web
python manage.py migrate
python manage.py createsuperuser
```

#### 2.3.3 配置 settings.py
在 `backend/backend/settings.py` 中：

**注册应用：**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'web',
    'corsheaders',
]
```

**添加跨域中间件：**
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 必须尽量靠前
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**设置时区：**
```python
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = True
```

**配置静态文件和媒体文件：**
```python
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = 'http://127.0.0.1:8000/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

**配置 JWT 认证：**
```python
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**配置跨域：**
```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
```

#### 2.3.4 配置 URL 路由
在 `backend/backend/urls.py` 中：
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
]

# 仅限开发阶段使用。生产阶段需要在nginx里配置。
if settings.DEBUG:
    urlpatterns += static(
        '/assets/',
        document_root=settings.BASE_DIR / 'static/frontend/assets'
    )
    urlpatterns += static(
        '/media/',
        document_root=settings.MEDIA_ROOT
    )
```

在 `backend/web/urls.py` 中：
```python
from django.urls import path
from .views.index import index

urlpatterns = [
    path('', index, name='index'),
]
```

创建 `backend/web/views/index.py`：
```python
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')
```

创建 `backend/web/templates/index.html`：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIFriends</title>
</head>
<body>
    <div id="app"></div>
    {% load static %}
    <script type="module" src="{% static 'frontend/assets/index.js' %}"></script>
</body>
</html>
```

### 2.4 创建前端

#### 2.4.1 创建 Vue 项目
```bash
cd AIFriends
npm create vue@latest

# 项目名称：frontend
# 选择功能：Router、Pinia

cd frontend
npm install
```

#### 2.4.2 安装 Tailwind CSS 和 DaisyUI
```bash
npm install -D tailwindcss @tailwindcss/vite
npm install -D daisyui
```

#### 2.4.3 配置 Vite
在 `frontend/vite.config.js` 中：
```javascript
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  build: {
    outDir: path.resolve(__dirname, '../backend/static/frontend'),
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
```

#### 2.4.4 配置 Tailwind CSS
在 `frontend/src/assets/main.css` 中：
```css
@import "tailwindcss";
@plugin "daisyui";
```

#### 2.4.5 配置 App.vue
在 `frontend/src/App.vue` 中：
```vue
<script setup>
import NavBar from "@/components/navbar/NavBar.vue";
</script>

<template>
  <NavBar>
    <RouterView />
  </NavBar>
</template>
```

#### 2.4.6 创建导航栏组件
创建 `frontend/src/components/navbar/NavBar.vue`：
```vue
<template>
  <div class="drawer lg:drawer-open">
    <input id="my-drawer-4" type="checkbox" class="drawer-toggle" />
    <div class="drawer-content flex min-h-screen flex-col">
      <nav class="navbar w-full shrink-0 bg-base-100 shadow-sm">
        <div class="navbar-start">
          <label for="my-drawer-4" aria-label="open sidebar" class="btn btn-square btn-ghost">
            <MenuIcon />
          </label>
          <div class="px-2 font-bold text-xl">AIFriends</div>
        </div>
        <div class="navbar-center w-4/5 max-w-180 flex justify-center">
          <div class="join w-4/5 flex justify-center">
            <input class="input join-item rounded-l-full w-4/5" placeholder="搜索你感兴趣的内容">
            <button class="btn join-item rounded-r-full gap-0">
              <SearchIcon />
              搜索
            </button>
          </div>
        </div>
        <div class="navbar-end">
          <RouterLink :to="{ name: 'register-index' }" active-class="Button-active" class="btn btn-ghost text-lg">注册</RouterLink>
          <RouterLink :to="{ name: 'login-index' }" active-class="Button-active" class="btn btn-ghost text-lg">登录</RouterLink>
        </div>
      </nav>
      <main class="min-h-0 flex-1 overflow-y-auto">
        <slot></slot>
      </main>
    </div>
    <div class="drawer-side is-drawer-close:overflow-visible">
      <label for="my-drawer-4" aria-label="close sidebar" class="drawer-overlay"></label>
      <div class="flex min-h-full flex-col items-start bg-base-200 is-drawer-close:w-16 is-drawer-open:w-54">
        <ul class="menu w-full grow">
          <li>
            <RouterLink :to="{ name: 'homepage-index' }" active-class="menu-focus" class="is-drawer-close:tooltip is-drawer-close:tooltip-right py-3" data-tip="首页">
              <HomepageIcon />
              <span class="is-drawer-close:hidden text-base ml-2 whitespace-nowrap">首页</span>
            </RouterLink>
          </li>
          <li>
            <RouterLink :to="{ name: 'friend-index' }" active-class="menu-focus" class="is-drawer-close:tooltip is-drawer-close:tooltip-right py-3" data-tip="好友">
              <FriendIcon />
              <span class="is-drawer-close:hidden text-base ml-2 whitespace-nowrap">好友</span>
            </RouterLink>
          </li>
          <li>
            <RouterLink :to="{ name: 'create-index' }" active-class="menu-focus" class="is-drawer-close:tooltip is-drawer-close:tooltip-right py-3" data-tip="创作">
              <CreateIcon />
              <span class="is-drawer-close:hidden text-base ml-2 whitespace-nowrap">创作</span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import MenuIcon from "@/components/navbar/icons/MenuIcon.vue";
import HomepageIcon from "@/components/navbar/icons/HomepageIcon.vue";
import FriendIcon from "@/components/navbar/icons/FriendIcon.vue";
import CreateIcon from "@/components/navbar/icons/CreateIcon.vue";
import SearchIcon from "@/components/navbar/icons/SearchIcon.vue";
</script>
```

需要创建对应的图标组件（MenuIcon.vue, HomepageIcon.vue 等）。

#### 2.4.7 创建页面视图
创建以下页面文件：
- `frontend/src/views/homepage/HomePageIndex.vue`
- `frontend/src/views/friend/FriendIndex.vue`
- `frontend/src/views/create/CreateIndex.vue`
- `frontend/src/views/user/account/LoginIndex.vue`
- `frontend/src/views/user/account/RegisterIndex.vue`
- `frontend/src/views/user/space/SpaceIndex.vue`
- `frontend/src/views/profile/ProfileIndex.vue`
- `frontend/src/views/error/NotFoundIndex.vue`

每个文件的基本结构：
```vue
<script setup>
</script>

<template>
  <div class="page-name">
    页面内容
  </div>
</template>

<style scoped>
</style>
```

#### 2.4.8 配置路由
在 `frontend/src/router/index.js` 中：
```javascript
import { createRouter, createWebHistory } from 'vue-router'
import HomepageIndex from "@/views/homepage/HomePageIndex.vue"
import FriendIndex from "@/views/friend/FriendIndex.vue"
import CreateIndex from "@/views/create/CreateIndex.vue"
import LoginIndex from "@/views/user/account/LoginIndex.vue"
import RegisterIndex from "@/views/user/account/RegisterIndex.vue"
import SpaceIndex from "@/views/user/space/SpaceIndex.vue"
import ProfileIndex from "@/views/profile/ProfileIndex.vue"
import NotFoundIndex from "@/views/error/NotFoundIndex.vue"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: HomepageIndex, name: 'homepage-index' },
    { path: '/friend', component: FriendIndex, name: 'friend-index' },
    { path: '/create', component: CreateIndex, name: 'create-index' },
    { path: '/login', component: LoginIndex, name: 'login-index' },
    { path: '/register', component: RegisterIndex, name: 'register-index' },
    { path: '/user/space', component: SpaceIndex, name: 'space-index' },
    { path: '/profile', component: ProfileIndex, name: 'profile-index' },
    { path: '/:pathMatch(.*)*', component: NotFoundIndex, name: 'not-found' },
  ],
})

export default router
```

### 2.5 合并前后端

#### 2.5.1 构建前端
```bash
cd frontend
npm run build
```

构建产物会自动输出到 `backend/static/frontend/` 目录（已在 `vite.config.js` 中配置）。

#### 2.5.2 运行后端
```bash
cd backend
python manage.py runserver
```

访问 `http://127.0.0.1:8000/` 即可查看应用。

### 2.6 创建并维护 Git 仓库

#### 2.6.1 创建 .gitignore
在项目根目录创建 `.gitignore`：
```
__pycache__/
*.py[cod]
.idea/
db.sqlite3
media/
staticfiles/
static/
.venv/
node_modules/
dist/
```

#### 2.6.2 初始化 Git 仓库
```bash
git init
git add .
git commit -m "Initial commit: AIFriends project setup"
```

#### 2.6.3 推送到远程仓库
```bash
# 在 GitHub 创建仓库后（仓库地址：https://github.com/ppshuX/AIFriends）
git remote add origin https://github.com/ppshuX/AIFriends.git
git branch -M master
git push -u origin master
```

## 3. 提交记录

根据项目开发过程，Lesson 1 的主要提交包括：

1. **Initial commit: AIFriends project setup** - 项目初始化
2. **Clean up frontend example code** - 清理前端示例代码
3. **Add frontend deployment scripts and configure Tailwind CSS** - 配置 Tailwind CSS
4. **feat: implement routing and wire NavBar to views** - 实现路由和导航栏

## 4. 参考资料

- [项目 GitHub 仓库](https://github.com/ppshuX/AIFriends)
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [DaisyUI 组件库](https://daisyui.com/)
- [Django 官方文档](https://docs.djangoproject.com/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)
