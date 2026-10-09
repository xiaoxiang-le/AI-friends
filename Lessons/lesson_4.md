# Lesson 4：流式布局

---

## 上节课的补丁

1. **创作按钮路由**：将导航栏中的创作按钮的路由重置成 **create-index**（对应 `/create/`、CreateIndex 页面）。
2. **删除角色前清理图片**：在 `AIFriends/backend/web/views/create/character/remove.py` 中添加逻辑：**删除角色前，先删除头像和背景图片**。
   - 使用 `Character.objects.get(pk=character_id, author__user=request.user)` 取出角色实例；
   - 调用 `remove_old_photo(character.photo)`、`remove_old_photo(character.background_image)`；
   - 再执行 `character.delete()`。  
   （注意：不要写成 `character = ...get().delete()`，否则得到的是删除结果而非模型实例，无法用于删图。）

---

## 1. 实现个人主页

### 1.1 创建后端

在 `AIFriends/backend/web/views/create/character/` 目录下实现：

**get_list.py**：返回**角色列表**和**作者信息**。

- GET 请求，从 `request.query_params` 取 `items_count`、`user_id`。
- 根据 `user_id` 找到对应用户及 `UserProfile`，再按 `author=user_profile` 筛选角色，按 `-id` 排序，分页切片 `[items_count: items_count + 20]`。
- 返回 `result: 'success'`、`user_profile`（含 `user_id, username, profile, photo`）、`characters`（列表，每项含 `id, name, profile, photo.url, background_image.url, author` 等）。

在 `AIFriends/backend/web/urls.py` 中**添加路由**：`path('api/create/character/get_list/', GetListCharacterView.as_view())`。

### 1.2 实现前端

**1.2.1 空组件**

- 在 `AIFriends/frontend/src/views/user/space/components/` 下创建 **UserInfoField.vue**：展示个人信息（头像、用户名、AIFriends 号、简介等）。
- 在 `AIFriends/frontend/src/components/character/` 下创建 **Character.vue**：展示角色卡片（背景图、头像、名字、简介、作者信息；可选编辑/删除按钮）。

**1.2.2 在 SpaceIndex.vue 中对接后端**

在 `AIFriends/frontend/src/views/user/space/SpaceIndex.vue` 中：

- 调用 `get_list` 接口，维护 `userProfile`、`characters`、`hasCharacters`、`isLoading` 等状态。

**网格布局**：可以根据屏幕宽度自动决定每行的元素数量，并将元素均匀排列在屏幕上；当最后一行元素不足时会左对齐。

```html
<div class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-9 mt-12 justify-items-center w-full px-9">
  ...
</div>
```

**渐变色**：最下面是黑色 40% 透明，最上面是完全透明。

```html
<!-- 用在卡片等容器上 -->
class="... bg-linear-to-t from-black/40 to-transparent"
```

**流式加载新角色**：使用哨兵元素 + `IntersectionObserver`，哨兵进入视口时调用 `loadMore()` 请求下一页，直到返回列表为空则设 `hasCharacters = false`。

```vue
<script setup>
const sentinelRef = useTemplateRef('sentinel-ref')
let observer = null

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

onMounted(async () => {
  await loadMore()  // 加载新元素

  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadMore()
        }
      })
    },
    {root: null, rootMargin: '2px', threshold: 0}
  )

  // 监听哨兵元素，每次哨兵被看到时，都会触发一次
  observer.observe(sentinelRef.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()  // 解绑监听器
})
</script>

<template>
  ...
  <!-- 设置哨兵 -->
  <div ref="sentinel-ref" class="h-2"></div>
  ...
</template>
```

**修改角色、删除角色**：

- 修改：卡片上编辑按钮跳转至更新角色页（如 `update-character`），params 带 `character_id`。
- 删除：卡片上删除按钮调用 `POST /api/create/character/remove/`，body 传 `character_id`；成功后从列表中移除该项（如 `emit('remove', character.id)` 由父组件处理）。

**建议自测**：

- 观察删除角色后，对应的头像和背景图片是否在 `backend/media/` 下被删除。
- 观察流式加载：滚动到底部是否自动加载新角色。
- 用其他账号再创建一个角色，确认个人主页只显示当前用户空间的角色。

### 1.3 将前端代码打包到后端

删除调试信息后执行前端构建，将产物部署到后端静态/模板目录（与项目既有打包方式一致）。

---

## 2. 实现首页

### 2.1 创建后端

在 `AIFriends/backend/web/views/homepage/` 目录下实现：

**index.py**：返回**所有角色**列表（分页）。

- GET 请求，从 `request.query_params` 取 `items_count`（可默认 0），按 `-id` 排序，切片 `[items_count: items_count + 20]`。
- 返回 `result: 'success'`、`characters`（结构与个人主页单条角色一致，含 `author` 等）。

在 `AIFriends/backend/web/urls.py` 中**添加路由**：`path('api/homepage/index/', HomepageIndexView.as_view())`。

### 2.2 实现前端

实现 **AIFriends/frontend/src/views/homepage/HomepageIndex.vue**：

- 与 SpaceIndex 类似：流式加载、哨兵、网格布局；请求 `GET /api/homepage/index/`，params 传 `items_count`。
- 首页不传 `user_id`，展示全部角色。

### 2.3 添加搜索功能

**2.3.1 导航栏（NavBar.vue）**

在 `AIFriends/frontend/src/components/navbar/NavBar.vue` 中添加搜索逻辑：

- **点击搜索按钮后**：打开首页，并将搜索文本添加到 url 的 **query 参数**中（如 `q`）。
- **监听 `route.query.q`**：将最新值赋给 `searchQuery`。这样刷新页面后，搜索文本才能自动填充到搜索框内。

**2.3.2 首页（HomepageIndex.vue）**

在 `AIFriends/frontend/src/views/homepage/HomepageIndex.vue` 中：

- 将搜索文本添加到请求中（如 params 传 `search_query: route.query.q || ''`）。
- **当 query 参数变化时**自动重新获取角色列表（如 watch `route.query.q`，清空列表、重置分页后再调用 `loadMore()`）。

**2.3.3 后端支持搜索**

在 `AIFriends/backend/web/views/homepage/index.py` 中实现对搜索的支持：

- 从 `request.query_params` 取 `search_query`（可选，默认空）。
- 若 `search_query` 非空，使用 `Q(name__icontains=search_query) | Q(profile__icontains=search_query)` 过滤后再分页；否则查询全部角色。
- 分页仍为 `[items_count: items_count + 20]`。

### 2.4 将前端代码打包到后端

同 1.3。

---

## 3. 实现好友页面

### 3.1 创建后端

**3.1.1 创建数据库**

在 `AIFriends/backend/web/models/friend.py` 中创建 **Friend** 数据库（模型）。

- 字段示例：当前用户（如 `me` → UserProfile）、角色（`character` → Character）、记忆/备注（如 `memory`）、创建/更新时间等。
- **`character = models.ForeignKey(Character, on_delete=models.CASCADE)`**：当删除 character 时，会自动将关联的 friend 删掉（级联删除）。

**3.1.2 创建 views**

在 `AIFriends/backend/web/views/friend/` 目录下实现：

- **get_or_create.py**：如果有该好友，则返回；如果没有，则创建并返回（入参如 `character_id`，当前用户从 `request.user` 取）。
- **remove.py**：删除好友（如按 `friend_id` + 当前用户校验后删除）。
- **get_list.py**：获取好友列表（分页，如 `items_count`，每页 20 条，按 `update_time` 倒序等）。

**3.1.3 实现路由**

在 `AIFriends/backend/web/urls.py` 中为上述三个接口添加路由（如 `api/friend/get_or_create/`、`api/friend/remove/`、`api/friend/get_list/`）。

### 3.2 实现前端

**3.2.1 创建聊天界面组件**

在 `AIFriends/frontend/src/components/character/chat_field/` 目录下创建：

- **ChatField.vue**：显示聊天界面（含背景、消息区、输入区等）。
- **input_field/InputField.vue**：聊天输入框。
- **character_photo_field/CharacterPhotoField.vue**：虚拟角色头像。

将**模态框背景图片**设置成聊天背景（使用好友对应角色的 `background_image`）：

```js
const modalStyle = computed(() => {
  if (props.friend) {
    return {
      backgroundImage: `url(${props.friend.character.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
  } else {
    return {}
  }
})
```

在 **AIFriends/frontend/src/components/character/Character.vue** 中实现：**点击角色卡片后，自动打开聊天界面**（即打开上述 ChatField 的模态框）。

**3.2.2 实现好友列表页面**

- 实现 **AIFriends/frontend/src/views/friend/FriendIndex.vue**：展示好友列表（可复用角色卡片或类似布局）。
- **实现删除好友功能**：调用 `api/friend/remove/`，传入 `friend_id`，成功后从列表中移除该项。
- **阻止卡片内的点击事件向上传播**：在卡片内按钮（如删除）上使用 **`@click.stop`**（课程原文写为 `@click.top`，实际应为 `@click.stop`），避免触发卡片本身的“打开聊天”等外层点击。

**级联删除说明**：因 `character = models.ForeignKey(Character, on_delete=models.CASCADE)`，当删除某个角色时，会自动将关联的 Friend 记录删掉，无需在前端或接口中单独删好友。

### 3.3 将前端代码打包到后端

同 1.3，将前端构建产物部署到后端。

---

## 小结

| 模块     | 后端 | 前端 |
|----------|------|------|
| 个人主页 | get_list（角色列表 + 作者信息）、remove 前删头像/背景 | UserInfoField、Character、SpaceIndex、网格、渐变、流式加载、修改/删除角色 |
| 首页     | homepage/index（全角色分页） | HomepageIndex、流式加载 |
| 搜索     | index 支持 search_query | NavBar 跳首页带 q、监听 query 回填、HomepageIndex 带 search_query 并随 query 重载 |
| 好友     | Friend 模型、get_or_create/remove/get_list | ChatField、InputField、CharacterPhotoField、Character 点开聊天、FriendIndex、删除好友、@click.stop |

**路由汇总（本节涉及）**：

- `api/create/character/get_list/`、`api/create/character/remove/`
- `api/homepage/index/`
- `api/friend/get_or_create/`、`api/friend/remove/`、`api/friend/get_list/`

**前端要点**：创作按钮 → `create-index`；网格 `grid-cols-[repeat(auto-fill,minmax(240px,1fr))]`；渐变 `from-black/40 to-transparent`；流式加载哨兵 + IntersectionObserver；搜索用 query `q` 与后端 `search_query`；好友卡片内操作用 `@click.stop`。
