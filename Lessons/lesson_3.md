## Lesson 3：编辑资料、编辑角色模块

本节课在 Lesson 2 的基础上，完成 **用户编辑资料**（头像、用户名、简介）与 **角色 CRUD 后端**（创建、更新、删除、获取单条），并接入 Croppie 裁剪头像、base64 转文件上传。

---

### 0. 上节课补丁

- 减小用户下拉菜单宽度（如 `UserMenu.vue` 中 dropdown 宽度）。
- 用户下拉菜单中的用户名为英文时也支持省略号：可对用户名容器加 `break-all`、`line-clamp-1` 等。
- 在 `backend/web/urls.py` 中添加匹配任意路径的路由，使前端 history 模式下任意路径刷新都由 Django 落到根路径，再由前端路由接管：

```python
re_path(r"^(?!media/|static/|assets/).*$", index),
```

---

### 1. 实现编辑资料页面

#### 1.1 创建后端

**1.1.1 辅助函数 `remove_old_photo`**

`backend/web/views/utils/photo.py`：删除旧图片，避免默认头像被删。

```python
import os
from django.conf import settings

def remove_old_photo(photo):
    if photo and photo.name != 'user/photos/default.png':
        old_path = settings.MEDIA_ROOT / photo.name
        if os.path.exists(old_path):
            os.remove(old_path)
```

**1.1.2 更新资料接口**

`backend/web/views/user/profile/update.py`：接收 `username`、`profile`（`request.data`）、`photo`（`request.FILES`），更新 `User` 与 `UserProfile`，并返回新 `user_id/username/profile/photo`。

- 使用 `UserProfile.objects.filter(user=user).first()` 取当前用户资料；若不存在返回 400。
- 校验用户名非空、简介非空；若改用户名则检查是否与已有用户重复。
- 若有新 `photo`，先 `remove_old_photo(user_profile.photo)`，再赋值并 `save()`。
- 更新 `user_profile.profile`、`user_profile.update_time`、`user.username` 后保存。
- 返回 `result: 'success'` 及最新 `user_id, username, profile, photo`（`photo` 用 `user_profile.photo.url`）。

**1.1.3 路由**

在 `backend/web/urls.py` 中增加：

```python
path('api/user/profile/update/', UpdateProfile.as_view()),
```

---

#### 1.2 创建前端

**1.2.1 安装 Croppie**

vue-croppie 不支持 Vue3，直接使用 croppie：

```bash
cd frontend && npm install croppie
```

使用要点（见 `frontend/src/views/user/profile/components/Photo.vue`）：

- 引入：`import Croppie from "croppie"; import "croppie/croppie.css";`
- 选图后 `FileReader.readAsDataURL(file)`，在 `onload` 里打开弹窗并 `croppie.bind({ url: photo })`。
- 裁剪结果用 **base64** 与课程一致：`myPhoto.value = await croppie.result({ type: "base64", size: "viewport" });`
- 弹窗内容器：每次打开前清空并新建一个 wrapper div 再 `new Croppie(wrapper, {...})`，避免 “Can't initialize croppie more than once”。
- `modal-box` 与 croppie 样式冲突时，为 modal 内容加 `transition-none`。
- 组件卸载时 `croppie?.destroy()`，防止内存泄漏。

**1.2.2 头像、用户名、简介组件**

- `frontend/src/views/user/profile/components/Photo.vue`：头像展示 + 点击选图、弹窗内 Croppie 裁剪；`defineExpose({ myPhoto })` 供父组件读取；开发环境下对 `/media/` 相对路径拼 `BASE_URL` 以正确显示。
- `frontend/src/views/user/profile/components/Username.vue`：`props.username` + `ref(myUsername)`，`watch` 监听 `props.username` 与 `myUsername`，并 `defineExpose({ myUsername })`。
- `frontend/src/views/user/profile/components/Profile.vue`：同上，`profile` / `myProfile`，`defineExpose({ myProfile })`。

**1.2.3 资料编辑页**

`frontend/src/views/user/profile/ProfileIndex.vue`：

- 使用 `useTemplateRef('photo-ref'|'username-ref'|'profile-ref')` 获取子组件实例。
- 表单项：`<Photo ref="photo-ref" :photo="user.photo" />`、`<Username ref="username-ref" :username="user.username" />`、`<Profile ref="profile-ref" :profile="user.profile" />`。
- 提交时从 `photoRef.value.myPhoto`、`usernameRef.value.myUsername`、`profileRef.value.myProfile` 取值；仅当 `photo !== user.photo` 且为 data URL（`photo.startsWith("data:")`）时用 `base64ToFile(photo, "photo.png")` 得到 File 并 append 到 FormData。
- `api.post('/api/user/profile/update/', formData)`，成功后 `user.setUserInfo(data)`。

路由（`frontend/src/router/index.js`）示例：

```javascript
{ path: '/user/profile/', component: ProfileIndex, name: 'user-profile-index', meta: { needLogin: true } },
```

---

#### 1.3 对接前后端

**1.3.1 base64 转可上传文件**

`frontend/src/js/utils/base64_to_file.js`：

```javascript
export function base64ToFile(base64, filename) {
  const arr = base64.split(',')
  const mime = arr[0].match(/:(.*?);/)[1]
  const bstr = atob(arr[1])
  let n = bstr.length
  const u8arr = new Uint8Array(n)
  while (n--) u8arr[n] = bstr.charCodeAt(n)
  return new File([u8arr], filename, { type: mime })
}
```

注意：仅当入参为 **data URL**（`data:image/xxx;base64,...`）时有效；Croppie 使用 `type: 'base64'` 时得到的就是该格式。

**1.3.2 观察图片更新**

上传/更新头像后，可在 `backend/media/user/photos/` 下查看：旧头像被删除、新文件按 `user/photos/{user_id}/{uuid}.ext` 生成。

---

### 2. 实现编辑角色模块（后端）

#### 2.1 创建数据库

`backend/web/models/character.py`：

- `Character` 模型：`author`（ForeignKey → UserProfile）、`name`、`photo`、`profile`、`background_image`、`create_time`、`update_time`。
- `photo` / `background_image` 使用 `upload_to` 函数，路径如 `charactere/photos/{author.user_id}_{filename}`。
- 时间字段使用 `default=now`（`from django.utils.timezone import now`）。

创建/更新迁移并应用：

```bash
cd backend
python manage.py makemigrations web
python manage.py migrate
```

#### 2.2 创建 views

**2.2.1 创建角色**  
`backend/web/views/create/character/create.py` — `CreateCharacterView`：

- POST：`request.data` 取 `name`、`profile`；`request.FILES` 取 `photo`、`background_image`。
- 校验非空后，`UserProfile.objects.get(user=request.user)` 作为 `author`，`Character.objects.create(...)`。
- 成功返回 `{'result': 'success'}`。

**2.2.2 更新角色**  
`backend/web/views/create/character/update.py` — `UpdateCharacterView`：

- POST：`request.data` 取 `character`（id）、`name`、`profile`；`request.FILES` 取 `photo`、`background_image`（可选）。
- `Character.objects.get(id=character_id, author__user=request.user)`，若有新 `photo`/`background_image` 则 `remove_old_photo` 后替换，再更新 `name`、`profile`、`update_time`（`django.utils.timezone.now()`）并 `save()`。
- 成功返回 `{'result': 'success'}`。

**2.2.3 删除角色**  
`backend/web/views/create/character/remove.py` — `RemoveCharacter`：

- POST：`request.data.get('character_id')`，`Character.objects.filter(pk=..., author__user=request.user).delete()`，成功返回 `{'result': 'success'}`。

**2.2.4 获取单条角色**  
`backend/web/views/create/character/get_single.py` — `GetSingleCharacterView`：

- GET：`request.query_params.get('character_id')`，按 id 与当前用户过滤，返回 `{'result': 'success', 'character': { id, name, profile, photo.url, background_image.url }}`。

说明：GET 参数在 `request.query_params`，POST 表单/JSON 在 `request.data`，文件在 `request.FILES`。

#### 2.3 路由

在 `backend/web/urls.py` 中：

```python
from .views.create.character.create import CreateCharacterView
from .views.create.character.update import UpdateCharacterView
from .views.create.character.remove import RemoveCharacter
from .views.create.character.get_single import GetSingleCharacterView

urlpatterns = [
    # ...
    path('api/create/character/create/', CreateCharacterView.as_view()),
    path('api/create/character/update/', UpdateCharacterView.as_view()),
    path('api/create/character/remove/', RemoveCharacter.as_view()),
    path('api/create/character/get_single/', GetSingleCharacterView.as_view()),
    # ...
    re_path(r"^(?!media/|static/|assets/).*$", index),
]
```

---

### 3. 小结

| 模块       | 后端 | 前端 |
|------------|------|------|
| 编辑资料   | `remove_old_photo`、`UpdateProfile`、`api/user/profile/update/` | Croppie、Photo/Username/Profile、ProfileIndex、base64ToFile、FormData 上传 |
| 编辑角色   | Character 模型、CreateCharacterView、UpdateCharacterView、RemoveCharacter、GetSingleCharacterView 及对应路由 | 后续课程或自行实现创建/编辑/删除角色页面并调用上述接口 |

编辑资料流程：选图 → Croppie 裁剪得到 base64 → 仅当为新图且为 data URL 时 base64ToFile 转 File → FormData 提交 `/api/user/profile/update/` → 后端更新 User + UserProfile 并删除旧头像文件。
