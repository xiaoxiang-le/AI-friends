# Lesson 3.5：编辑资料、编辑角色模块

本节课完成 **用户编辑资料**（头像、用户名、简介）与 **角色 CRUD**（创建、更新、删除、获取单条），并接入 Croppie 裁剪、base64 转文件上传。

---

## 上节课的补丁

1. **减小用户下拉菜单宽度**，使布局更紧凑。
2. **用户下拉菜单中的用户名**：中文时可自动省略号，英文时可通过 `break-all`、`line-clamp-1` 等样式同样支持省略。
3. **前端 history 模式刷新**：在 `AIFriends/backend/web/urls.py` 中添加匹配任意路径的路由，使任意路径刷新时 Django 都落到根路径，再由前端路由接管：

```python
re_path(r'^(?!media/|static/|assets/).*$', index)
```

---

## 1. 实现编辑资料页面

### 1.1 创建后端

**1.1.1 辅助函数 `remove_old_photo`**

在 `AIFriends/backend/web/views/utils/photo.py` 中实现：删除旧图片，避免误删默认头像。

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

实现 `AIFriends/backend/web/views/user/profile/update.py`：更新用户名、简介、头像等。

- 使用 `UserProfile.objects.filter(user=user).first()` 获取当前用户资料；不存在则返回错误。
- 校验用户名、简介非空；若修改用户名需检查是否与已有用户重复。
- 若有新头像，先 `remove_old_photo(user_profile.photo)`，再赋值并保存。
- 更新 `user_profile.profile`、`user_profile.update_time`、`user.username` 后保存。
- 返回 `result: 'success'` 及最新 `user_id, username, profile, photo`（`photo` 使用 `user_profile.photo.url`）。

**1.1.3 路由**

在 `AIFriends/backend/web/urls.py` 中添加：

```python
path('api/user/profile/update/', UpdateProfile.as_view()),
```

---

### 1.2 创建前端

**1.2.1 安装 Croppie**

vue-croppie 不支持 Vue3，直接使用 croppie：

```bash
cd frontend && npm install croppie
```

使用方式示例：

```vue
<script setup>
import Croppie from 'croppie'
import 'croppie/croppie.css'

const croppieRef = useTemplateRef('croppie-ref')
let croppie = null

// 打开裁剪时
if (!croppie) {
  croppie = new Croppie(croppieRef.value, {
    viewport: { width: 200, height: 200, type: 'square' },
    boundary: { width: 300, height: 300 },
    enableOrientation: true,
    enforceBoundary: true,
  })
}
croppie.bind({ url: photo })

// 获取裁剪结果
myPhoto.value = await croppie.result({
  type: 'base64',
  size: 'viewport',
})

onBeforeUnmount(() => {
  croppie?.destroy()
})
</script>

<template>
  <div ref="croppie-ref" class="flex flex-col my-4"></div>
</template>
```

注意：模态框的 `modal-box` 与 croppie 样式冲突会导致裁剪区域右下角多缝隙，可给 `modal-box` 加上 `transition-none` 修复。

**1.2.2 创建头像、用户名、简介组件**

在 `AIFriends/frontend/src/views/user/profile/components/` 下创建：

- **Photo.vue**：用户头像（选图、裁剪、展示）
- **Username.vue**：用户名输入
- **Profile.vue**：简介输入

需用 `watch` 监听用户信息变化：刷新页面时用户信息从云端拉取，拉取后需同步到编辑页。

关闭按钮可使用：`✕`

**1.2.3 创建资料编辑页面**

实现 `AIFriends/frontend/src/views/user/profile/ProfileIndex.vue`，组装 Photo、Username、Profile 组件，提交时调用 `/api/user/profile/update/`。

---

### 1.3 对接前后端

**1.3.1 将 base64 图片转为可上传文件**

在 `AIFriends/frontend/src/js/utils/base64_to_file.js` 中实现：

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

仅当入参为 **data URL**（`data:image/xxx;base64,...`）时有效；Croppie `type: 'base64'` 得到即该格式。提交时仅当头像为新裁剪（如 `photo.startsWith("data:")`）时再调用 `base64ToFile` 并 append 到 FormData。

**1.3.2 观察图片更新**

上传/更新头像后，在 `AIFriends/backend/media/user/photos/` 下可观察：旧图片被删除、新图片按配置路径生成。

---

## 2. 实现编辑角色页面

### 2.1 创建后端

**2.1.1 创建数据库**

在 `AIFriends/backend/web/models/character.py` 中创建 Character 模型：

- 字段：`author`（ForeignKey → UserProfile）、`name`、`photo`、`profile`、`background_image`、`create_time`、`update_time`。
- `photo` 的 `upload_to` 如：`character/photos/{instance.author.user_id}_{filename}`。
- `background_image` 的 `upload_to` 如：`character/background_images/{instance.author.user_id}_{filename}`。
- 时间字段使用 `django.utils.timezone.now` 作为 `default`。

执行迁移：

```bash
cd backend
python manage.py makemigrations web
python manage.py migrate
```

**2.1.2 创建 views**

在 `AIFriends/backend/web/views/create/character/` 下实现：

| 文件 | 说明 |
|------|------|
| **create.py** | 创建角色。POST：`request.data` 取 `name`、`profile`；`request.FILES` 取 `photo`、`background_image`。校验非空后 `Character.objects.create(...)`，返回 `{'result': 'success'}`。 |
| **update.py** | 更新角色。POST：`request.data['character_id']`、`request.data['name']`、`request.data['profile']`；`request.FILES` 取 `photo`、`background_image`（可选）。有新媒体时先 `remove_old_photo` 再替换，更新 `name`、`profile`、`update_time` 后 `save()`。 |
| **remove.py** | 删除角色。POST：`request.data['character_id']`，按 id 与当前用户过滤后 `delete()`，返回 `{'result': 'success'}`。类名为 `RemoveCharacterView`。 |
| **get_single.py** | 获取单条角色。GET：`request.query_params.get('character_id')`，按 id 与当前用户过滤，返回 `{'result': 'success', 'character': { id, name, profile, photo.url, background_image.url }}`。 |

注意：**GET 请求参数在 `request.query_params`**；**POST 请求参数在 `request.data`**，文件在 `request.FILES`。

**2.1.3 实现路由**

在 `AIFriends/backend/web/urls.py` 中添加：

```python
from .views.create.character.create import CreateCharacterView
from .views.create.character.get_single import GetSingleCharacterView
from .views.create.character.remove import RemoveCharacterView
from .views.create.character.update import UpdateCharacterView

# 在 urlpatterns 中：
path('api/create/character/create/', CreateCharacterView.as_view()),
path('api/create/character/update/', UpdateCharacterView.as_view()),
path('api/create/character/remove/', RemoveCharacterView.as_view()),
path('api/create/character/get_single/', GetSingleCharacterView.as_view()),
```

---

### 2.2 创建前端

**2.2.1 创建头像、名字、角色介绍、背景图片组件**

在 `AIFriends/frontend/src/views/create/character/components/` 下创建：

- **Photo.vue**：头像（Croppie 裁剪，与编辑资料类似）
- **Name.vue**：名字输入
- **Profile.vue**：角色介绍（多行文本）
- **BackgroundImage.vue**：聊天背景（Croppie 裁剪，viewport 比例可按 3:5 等设置）

**2.2.2 实现创建角色页面**

实现 `AIFriends/frontend/src/views/create/character/CreateCharacter.vue`：

- 使用 `useTemplateRef` 获取 Photo、Name、Profile、BackgroundImage 子组件。
- 校验头像、名字、角色介绍、聊天背景均非空。
- 使用 `base64ToFile` 将头像和背景的 base64 转为 File，与 `name`、`profile` 一起放入 FormData，POST 到 `/api/create/character/create/`。
- 成功后可跳转到用户空间（如 `user-space-index`）。

---

### 2.3 对接前后端

- 创建角色：FormData 字段 `name`、`profile`、`photo`、`background_image`，后端从 `request.data` 与 `request.FILES` 读取。
- 调试时可用课程提供的头像/背景示例图验证裁剪与上传。

---

### 2.4 实现更新角色页面

在 CreateCharacter 基础上实现 **UpdateCharacter.vue**：

- 路由参数获取 `character_id`（如 `route.params.character_id`）。
- `onMounted` 时 GET `/api/create/character/get_single/?character_id=xxx` 拉取当前角色，将返回的 `character` 赋给 `ref`，并作为 props 传给 Photo、Name、Profile、BackgroundImage（`:photo="character.photo"` 等）做回显。
- 提交时 FormData 包含 `character_id`、`name`、`profile`；仅当头像/背景与原始值不同时再 append `photo`、`background_image`（base64 需经 `base64ToFile` 转 File）。
- POST 到 `/api/create/character/update/`，成功后跳转用户空间。

在 `AIFriends/frontend/src/router/index.js` 中添加路由，例如：

```javascript
{
  path: '/create/character/update/:character_id/',
  component: UpdateCharacter,
  name: 'update-character',
  meta: { needLogin: true }
}
```

---

## 3. 将前端代码打包到后端

- 删除调试信息（如多余 `console.log`）。
- 执行前端构建（如 `npm run build`），将生成的静态资源部署到后端（如复制到 `backend/static/`、`backend/templates/` 或按现有部署脚本处理），使生产环境下刷新任意前端路由仍由 Django 返回 index 并由前端接管路由。

---

## 小结

| 模块 | 后端 | 前端 |
|------|------|------|
| 编辑资料 | `remove_old_photo`、`UpdateProfile`、`api/user/profile/update/` | Croppie、Photo/Username/Profile、ProfileIndex、base64ToFile |
| 编辑角色 | Character 模型、create/update/remove/get_single 四个接口及路由 | CreateCharacter、UpdateCharacter、Photo/Name/Profile/BackgroundImage、get_single 回显、FormData 提交 |

编辑资料：选图 → Croppie 裁剪得 base64 → 仅新图且为 data URL 时 base64ToFile → FormData 提交 `/api/user/profile/update/`。  
编辑角色：创建/更新均用 FormData；更新页先 get_single 回显，再按需提交 `character_id`、`name`、`profile` 及变更后的 `photo`、`background_image`。
