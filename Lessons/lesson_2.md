## Lesson 2：登录模块与前后端对接

本节课在 Lesson 1 的基础上，完成了 **登录 / 注册 / 退出登录 / 刷新 token / 获取用户信息** 等认证逻辑，并将前端打包部署到后端，形成一个可刷新、可持久登录的完整流程。

---

### 0. 上节课补丁

- 删除示例文件：`AIFriends/main.py`。
- 调整 `NavBar.vue` 布局，使搜索框在大屏下水平居中。

---

### 1. 实现前端路由

#### 1.1 创建路由页面

在 `frontend/src/views` 下创建（或确认存在）以下页面组件：

- `homepage/HomepageIndex.vue`
- `friend/FriendIndex.vue`
- `create/CreateIndex.vue`
- `error/NotFoundIndex.vue`
- `user/account/LoginIndex.vue`
- `user/account/RegisterIndex.vue`
- `user/space/SpaceIndex.vue`
- `profile/ProfileIndex.vue`

#### 1.2 配置路由表

`frontend/src/router/index.js`：

```12:24:frontend/src/router/index.js
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: HomepageIndex, name: 'homepage-index', meta: { needLogin: false } },
    { path: '/friend', component: FriendIndex, name: 'friend-index', meta: { needLogin: true } },
    { path: '/create', component: CreateIndex, name: 'create-index', meta: { needLogin: true } },
    { path: '/login', component: LoginIndex, name: 'login-index', meta: { needLogin: false } },
    { path: '/register', component: RegisterIndex, name: 'register-index', meta: { needLogin: false } },
    { path: '/user/space', component: SpaceIndex, name: 'space-index', meta: { needLogin: true } },
    { path: '/profile', component: ProfileIndex, name: 'profile-index', meta: { needLogin: true } },
    { path: '/:pathMatch(.*)*', component: NotFoundIndex, name: 'not-found' },
  ],
})
```

`/:pathMatch(.*)*` 用于前端 404 匹配。

#### 1.3 将路由挂到页面与导航栏

- 在 `frontend/src/App.vue` 中使用 `<RouterView />`：

```33:36:frontend/src/App.vue
<template>
  <NavBar>
    <RouterView />
  </NavBar>
</template>
```

- 在 `frontend/src/components/navbar/NavBar.vue` 中使用 `<RouterLink>` 并通过 `active-class` 高亮当前页面。
- `SpaceIndex.vue` 中可使用路由参数展示 `user_id`（后续课程可继续扩展）。

---

### 2. 实现登录、注册前端页面

#### 2.1 登录页 `LoginIndex.vue`

- 表单字段：`username`、`password`。
- 前端校验：非空校验。
- 调用 `api.post('/api/user/account/login/', {...})`。
- 成功后：
  - `user.setAccessToken(data.access)`；
  - `user.setUserInfo(data)`；
  - `router.push({ name: 'homepage-index' })`。
- 失败时展示 `data.result` 作为错误提示。

#### 2.2 注册页 `RegisterIndex.vue`

- 表单字段：`username`、`password`、`passwordConfirm`。
- 校验逻辑：
  - 用户名 / 密码 / 确认密码均不能为空；
  - 两次密码一致；
  - 密码不少于 6 位。
- 成功创建账号后，同样写入 store 并跳转首页。

---

### 3. 实现登录、注册后端逻辑

#### 3.1 UserProfile 模型与默认头像

`backend/web/models/user.py`：

```8:18:backend/web/models/user.py
def photo_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex[:10]}.{ext}'
    return f'user/photos/{instance.user_id}/{filename}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # 默认头像路径相对于 MEDIA_ROOT，上传头像时使用 photo_upload_to
    photo = models.ImageField(default='user/photos/default.png', upload_to=photo_upload_to)
    profile = models.TextField(default='谢谢你的关注', max_length=500)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)
```

- 先安装 Pillow：`pip install Pillow`。
- `MEDIA_ROOT` = `backend/media`，默认头像：`backend/media/user/photos/default.png`。
- 在 `backend/web/admin.py` 中注册：

```3:8:backend/web/admin.py
from .models.user import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
```

- 每次改模型后在 `backend` 目录执行：
  - `python manage.py makemigrations`
  - `python manage.py migrate`
- 在后台为 `admin` 用户创建对应的 `UserProfile`。

#### 3.2 账号相关 views

路径：`backend/web/views/user/account/`。

- `login.py`：用户名 + 密码登录，生成 `RefreshToken`，返回 `access` 与用户信息，并通过 cookie 设置 `refresh_token`（开发环境 `secure=False`）。
- `register.py`：创建 `User` + 默认 `UserProfile`，同样返回 `access` 与用户信息，并设置 `refresh_token` cookie。
- `logout.py`：删除 cookie 中的 `refresh_token`，返回 `result: success`。
- `refresh_token.py`：从 cookie 读 `refresh_token`，验证并生成新的 `access`，在旋转模式下更新 `refresh_token` cookie。

#### 3.3 更新后端路由

`backend/web/urls.py`：

```1:19:backend/web/urls.py
from django.urls import path, re_path
from .views.index import index
from .views.user.account.get_user_info import GetUserInfo
from .views.user.account.logout import LogoutView
from .views.user.account.login import Login
from .views.user.account.register import Register
from .views.user.account.refresh_token import RefreshTokenView

urlpatterns = [
    path("api/user/account/login/", Login.as_view()),
    path("api/user/account/logout/", LogoutView.as_view()),
    path("api/user/account/register/", Register.as_view()),
    path("api/user/account/refresh_token/", RefreshTokenView.as_view()),
    path("api/user/account/get_user_info/", GetUserInfo.as_view()),
    path("", index, name="index"),
    # 前端 history 模式：除 media/static/assets 外的任意路径都交给前端路由
    re_path(r"^(?!media/|static/|assets/).*$", index),
]
```

---

### 4. 前后端对接与登录状态管理

#### 4.1 前端全局状态：`user.js`

`frontend/src/stores/user.js`：

```1:54:frontend/src/stores/user.js
export const useUserStore = defineStore('user', () => {
    const id = ref(0);
    const username = ref("");
    const photo = ref("");
    const profile = ref("");
    const accessToken = ref("");
    const hasPulledUserInfo = ref(false);

    function isLogin() { return !!accessToken.value }

    function setAccessToken(token) { accessToken.value = token; }

    function setUserInfo(data) {
        id.value = data.user_id;
        username.value = data.username;
        photo.value = data.photo;
        profile.value = data.profile;
    }

    function logout() {
        id.value = 0;
        username.value = "";
        photo.value = "";
        profile.value = "";
        accessToken.value = "";
        hasPulledUserInfo.value = false;
    }

    function setHasPulledUserInfo(newStatus) {
        hasPulledUserInfo.value = newStatus;
    }

    return {
        id,
        username,
        photo,
        profile,
        accessToken,
        hasPulledUserInfo,
        isLogin,
        setAccessToken,
        setUserInfo,
        logout,
        setHasPulledUserInfo,
    }
})
```

- 删除示例 store：`frontend/src/stores/counter.js`（如果还存在的话）。

#### 4.2 登录后导航栏行为

在 `NavBar.vue` 中根据登录状态显示不同按钮：

```23:33:frontend/src/components/navbar/NavBar.vue
<RouterLink v-if="user.isLogin()" :to="{ name: 'create-index' }" ...>创作</RouterLink>

<RouterLink v-if="user.hasPulledUserInfo && !user.isLogin()" :to="{ name: 'login-index' }" ...>
  登录
</RouterLink>
<UserMenu v-else-if="user.isLogin()" />
```

- `UserMenu.vue` 中实现个人空间、编辑资料、退出登录等入口，退出时调用后端 `/api/user/account/logout/` 接口并执行 `user.logout()`。
- 使用课程给出的 `closeMenu()` 函数，在点击菜单条目后自动关闭下拉菜单。

#### 4.3 封装 HTTP 请求：`api.js`

`frontend/src/js/http/api.js`：完全按照课件示例实现，关键点：

- 所有请求自动在 header 里附加 `Authorization: Bearer <accessToken>`。
- 响应拦截器：当返回 401 时，使用 cookie 中的 `refresh_token` 调用 `/api/user/account/refresh_token/`：
  - 刷新成功：更新 `accessToken`，并重放原请求；
  - 刷新失败：调用 `user.logout()`，清除本地登录状态。

#### 4.4 对接登录 / 注册 / 退出接口

- `LoginIndex.vue`：对接登录接口；
- `RegisterIndex.vue`：对接注册接口；
- `UserMenu.vue`：对接退出接口。

前端与后端返回的字段（`access`、`user_id`、`username`、`photo`、`profile`）已经对齐。

#### 4.5 路由守卫

在 `router/index.js` 中实现路由守卫，保护需要登录的页面：

```26:45:frontend/src/router/index.js
router.beforeEach((to, from, next) => {
  const user = useUserStore()

  const needLogin = to.meta.needLogin

  // 刷新页面时，先等 App.vue 里 get_user_info / 刷新 token 的流程跑完
  // 只有在已经确认拉取过用户信息之后，才根据 isLogin 做跳转判断
  if (!user.hasPulledUserInfo) {
    return next()
  }

  if (needLogin && !user.isLogin()) {
    return next({ name: 'login-index', query: { redirect: to.fullPath } })
  }

  if (user.isLogin() && (to.name === 'login-index' || to.name === 'register-index')) {
    return next({ name: 'homepage-index' })
  }

  return next()
})
```

#### 4.6 首次打开网站时，从云端加载用户信息

后端 `get_user_info.py`：

```8:20:backend/web/views/user/account/get_user_info.py
class GetUserInfo(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.get(user=user)
            return Response({
                'result': 'success',
                'user_id': user.id,
                'username': user.username,
                'photo': user_profile.photo.url,
                'profile': user_profile.profile,
            })
        except:
            return Response({'result': '系统异常，请稍后重试'})
```

前端 `App.vue` 在应用挂载时拉取一次用户信息，并在完成后根据结果决定是否重定向到登录页面（使用 `router.replace` 防止后退到受保护页面）：

```1:33:frontend/src/App.vue
onMounted(async () => {
  try {
    const res = await api.get("/api/user/account/get_user_info/");
    const data = res.data;
    if (data.result === "success") {
      user.setUserInfo(data);
    }
  } catch (error) {
    console.error(error);
  } finally {
    user.setHasPulledUserInfo(true);

    if (route.meta.needLogin && !user.isLogin()) {
      await router.replace({ name: "login-index" });
    }
  }
});
```

导航栏中的 `user.hasPulledUserInfo` 用于避免在用户信息未确定前显示“登录”按钮导致闪烁。

#### 4.7 将前端代码打包到后端

使用 `deploy-frontend.ps1` 脚本在项目根目录构建前端并输出到 `backend/static/frontend`，然后在 `backend/web/templates/index.html` 中引用最新构建出的 `index-*.js` 与 `index-*.css`，由 Django 提供静态资源。

另外在 `backend/web/urls.py` 中添加：

```9:16:backend/web/urls.py
re_path(r"^(?!media/|static/|assets/).*$", index),
```

确保在前端任意路由下刷新页面时，Django 始终返回同一个入口 HTML，后续路由交给 Vue Router 处理。

---

### 5. 本节关联的主要 commit

- `feat: implement auth flow and route guards`：实现认证流程与路由守卫。
- `fix: stabilize auth state and static frontend assets`：修复刷新页面掉线、同步静态资源文件名、补充 `get_user_info` 与 history 路由兜底等问题。

