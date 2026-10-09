# Lesson 5：文字聊天

---

## 上节课的补丁

**修复 bug**：在首页点进其他用户的个人空间后，再去右上角点击自己的个人空间，页面内容没更新。

---

## 1. 实现聊天后端

### 1.1 安装依赖

```bash
pip install langgraph langchain langchain-openai python-dotenv
```

- **langgraph / langchain / langchain-openai**：构建对话图与调用大模型。
- **python-dotenv**：从 `.env` 加载环境变量。

### 1.2 创建数据库

在 `AIFriends/backend/web/models/friend.py` 中创建 **Message** 模型，用于存储每条聊天记录。

字段示例：`friend`（ForeignKey → Friend）、`user_message`、`input`、`output`、`input_tokens`、`output_tokens`、`total_tokens`、`create_time`。注意对 `user_message`、`input`、`output` 做长度限制（如 500 / 10000 / 500），便于截断存储。

### 1.3 配置环境变量

- 注册阿里云并打开 [百炼平台](https://bailian.console.aliyun.com/cn-beijing/#/home)，在 **模型 → 秘钥管理** 中创建 API Key。
- 创建 `AIFriends/backend/.env`，内容示例：

```env
API_KEY=""   # 替换成自己的 API Key
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

- 在 `AIFriends/.gitignore` 中添加 `*.env`。若 `.env` 已被 git 跟踪，可执行：`git rm --cached -f backend/.env` 再提交。
- 在 `AIFriends/backend/backend/settings.py` 开头添加：

```python
from dotenv import load_dotenv
load_dotenv()
```

修改后需**重启 Django 服务**才能加载环境变量。

### 1.4 实现 chat 视图与 LangGraph

在 `AIFriends/backend/web/views/friend/message/chat/` 下创建：

**graph.py**：用 LangGraph 定义对话图。

- `ChatOpenAI` 使用 `os.getenv('API_KEY')`、`os.getenv('API_BASE')`，并设置 `streaming=True`、`model_kwargs={"stream_options": {"include_usage": True}}`。
- 状态类型示例（TypedDict）：

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

- 使用 **StateGraph** 建图（需从 `langgraph.graph` 导入 `StateGraph`），单节点调用 LLM，编译后返回。

**chat.py**：实现 `MessageChatView`。

- POST 接收 `friend_id`、`message`，校验好友归属当前用户。
- 调用 `ChatGraph.create_app()` 得到图，构造 `inputs = {"messages": [HumanMessage(message)]}`。
- 定义生成器 `event_stream()`：遍历 `app.stream(inputs, stream_mode="messages")`，对 `BaseMessageChunk` 若存在 `msg.content` 则 `yield f"data: {json.dumps({'content': msg.content}, ensure_ascii=False)}\n\n"`，并收集 `usage_metadata`；最后 `yield "data: [DONE]\n\n"`，再根据 `full_output`、`full_usage` 创建一条 **Message** 记录（注意对 `user_message`、`input`、`output` 等做截断）。
- 使用 **SSERenderer** 避免 DRF 对 SSE 的报错：

```python
class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'txt'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

class MessageChatView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SSERenderer]
    def post(self, request):
        ...
```

- 返回：`StreamingHttpResponse(event_stream(), content_type="text/event-stream")`，并设置 `response['Cache-Control'] = 'no-cache'`。

### 1.5 添加路由

在 `AIFriends/backend/web/urls.py` 中为 chat 视图添加路由（如 `path('api/friend/message/chat/', MessageChatView.as_view())`）。注意导入路径与项目一致（如 `web.views.friend.message.chat.chat`）。

---

## 2. 实现聊天前端基础

- 打开聊天弹窗后**自动聚焦输入框**：在 `ChatField.vue` 的 `showModal()` 中 `await nextTick()` 后调用 `inputRef.value?.focus?.()`，且需从 vue 导入 `nextTick`。
- 将输入框与发送逻辑对接后端：先可用普通 POST 调试接口是否通；后续改为流式请求（见第 3 节）。

**模态框背景图**：若前端跑在 `localhost:5173`、后端在 `127.0.0.1:8000`，背景图路径需拼成完整 URL。可从 `api.js` 导出 `resolveMediaUrl`，在 `ChatField` 的 `modalStyle` 中使用 `resolveMediaUrl(props.friend.character.background_image)`，避免图片请求到错误域名。

---

## 3. 实现流式回复

### 3.1 改造后端

在 **graph.py** 的 `ChatOpenAI` 中确保包含：

- `streaming=True`
- `model_kwargs={"stream_options": {"include_usage": True}}`

在 **chat.py** 的 `event_stream()` 中按 1.4 的格式逐块 `yield` 带 `content` 的 `data:` 行，并在流结束后创建 Message、返回 `StreamingHttpResponse`。

### 3.2 改造前端

安装 SSE 客户端：

```bash
npm install @microsoft/fetch-event-source
```

在 `AIFriends/frontend/src/js/http/streamApi.js` 中实现通用流式请求（可参考讲义或 demo）：

- 使用 `fetchEventSource(BASE_URL + url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': \`Bearer ${userStore.accessToken}\` }, body: JSON.stringify(options.body || {}), openWhenHidden: true, onopen, onmessage, onerror }`。
- **onopen**：若 `response.status === 401`，先调用 `api.post('/api/user/account/refresh_token/', {})` 刷新 token，再 `throw new Error("TOKEN_REFRESHED")` 触发 onerror 重试；否则检查 `response.ok` 与 `content-type` 是否包含 `text/event-stream`。
- **onmessage**：若 `msg.data === '[DONE]'` 则调用 `options.onmessage('', true)`；否则 `JSON.parse(msg.data)` 后调用 `options.onmessage(json, false)`。
- **onerror**：若 `err.message === "TOKEN_REFRESHED"` 则再次执行本次请求（重试）；否则调用 `options.onerror(err)` 并 `throw err`。

**BASE_URL**：开发环境可用 `'http://127.0.0.1:8000'`；若与 `api.js` 统一，可从 `api.js` 导出 `BASE_URL` 并在 `streamApi.js` 中引用。

在 **InputField.vue** 中：

- 使用 `streamApi('/api/friend/message/chat/', { body: { friend_id: props.friendId, message: content }, onmessage(data, isDone) { ... }, onerror() { ... } })` 替代普通 axios POST。
- 发送前先 `emit('pushBackMessage', { role: 'user', content, id: crypto.randomUUID() })`，再 `emit('pushBackMessage', { role: 'ai', content: '', id: crypto.randomUUID() })`（AI 条初始为空，由流式回调逐字追加）。
- 在 `onmessage` 中若 `!isDone && data.content` 则 `emit('addToLastMessage', data.content)`。
- 使用 `isProcessing` 防重复发送，在 `onmessage(isDone)`、`onerror` 和 `catch` 中都要在适当时机将 `isProcessing = false`。
- `defineEmits` 使用数组形式：`defineEmits(['pushBackMessage', 'addToLastMessage'])`。

---

## 4. 实现聊天记录的创建和加载

### 4.1 后端

- **chat.py**：在 `event_stream()` 中，流式循环结束后根据 `full_output`、`full_usage` 调用 `Message.objects.create(...)`，并截断 `user_message`、`input`、`output` 等字段。
- **get_history.py**：在 `AIFriends/backend/web/views/friend/message/get_history.py` 中实现 `GetHistoryView`。GET 请求从 `query_params` 取 `last_message_id`、`friend_id`，校验归属后按 `id` 倒序、`pk__lt=last_message_id`（若 `last_message_id > 0`）筛选，取前 10 条，返回 `result: 'success'`、`messages`（每项含 `id`、`user_message`、`output` 等）。
- 在 **urls.py** 中为 get_history 添加路由（如 `path('api/friend/message/get_history/', GetHistoryView.as_view())`）。

### 4.2 前端

**4.2.1 ChatField.vue**

- 定义 `history = ref([])`，用于存储当前会话的聊天列表。
- 实现 `handlePushBackMessage(msg)`：`history.value.push(msg)`，然后 `chatHistoryRef.value?.scrollToBottom()`。
- 实现 `handleAddToLastMessage(delta)`：`history.value.at(-1).content += delta`，再 `chatHistoryRef.value?.scrollToBottom()`。
- 实现 `handlePushFrontMessage(msg)`：`history.value.unshift(msg)`（注意是 **unshift** 不是 shift，用于加载更早的历史）。
- 给 **ChatHistory** 组件绑定 `ref="chat-history-ref"`，以便调用其 `scrollToBottom()`；传参 `:character="friend.character"`（传角色信息用于头像等，不要误传 `friend.history`）。
- 模态框背景图使用 `resolveMediaUrl(props.friend.character.background_image)`（见第 2 节）。

**4.2.2 ChatHistory 与 Message 组件**

在 `AIFriends/frontend/src/components/character/chat_field/` 下（或按项目结构的 `input_field/chathistory/`）实现：

- **ChatHistory.vue**：接收 `history`、`friendId`、`character`，用 `v-for` 渲染每条 `Message`；内部维护 `lastMessageId`、`hasMessages`、`isLoading`，在挂载时调用 `loadMore()`，并用 **IntersectionObserver** 监听哨兵元素，哨兵进入可视区域时再次 `loadMore()`。
- **message/Message.vue**：接收 `message`、`character`，根据 `message.role` 渲染用户/AI 气泡；头像使用 **`:src` 绑定**（不要用 `src="character.photo"` 否则会被打包工具当模块解析）。若图片路径为相对路径，可用 `resolveMediaUrl(character?.photo)`、`resolveMediaUrl(user.photo)`（user 来自 `useUserStore()`）。聊天气泡加上 `whitespace-pre-wrap` 保留空格和换行。

**4.2.3 聊天记录自动滚动**

在 ChatHistory 中：

```js
const scrollRef = useTemplateRef('scroll-ref')

async function scrollToBottom() {
  await nextTick()
  scrollRef.value.scrollTop = scrollRef.value.scrollHeight
}
```

并通过 `defineExpose({ scrollToBottom })` 暴露给父组件；父组件在每次追加消息后调用 `chatHistoryRef.value?.scrollToBottom()`。

**4.2.4 隐藏滚动条**

```vue
<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
```

**4.2.5 流式加载更多历史**

- 请求 `GET /api/friend/message/get_history/`，params 传 `last_message_id`、`friend_id`。变量名与请求参数一致（如统一用 `lastMessageId`），避免请求一直带 0。
- 每次拉取到新消息后，用 `emit('pushFrontMessage', ...)` 按条 **unshift** 到父组件的 `history`（每条历史记录可包含 `role: 'ai'`/`'user'`、`content`、`id`）。
- **加载更多后保持滚动视觉位置**：在 `loadMore()` 中，插入新内容前记录 `oldHeight = scrollRef.value.scrollHeight`、`oldTop = scrollRef.value.scrollTop`；`await nextTick()` 后设置 `scrollRef.value.scrollTop = oldTop + scrollRef.value.scrollHeight - oldHeight`。
- **哨兵与 IntersectionObserver**：在滚动容器内放一个哨兵元素（如 `<div ref="sentinel-ref" class="h-2"></div>`）。判断哨兵是否“被看到”时，应判断**与滚动容器 `scrollRef` 的交集**（与视窗的交集在“加载更多历史”场景下不合适）：

```js
function checkSentinelVisible() {
  if (!sentinelRef.value) return false
  const sentinelRect = sentinelRef.value.getBoundingClientRect()
  const scrollRect = scrollRef.value.getBoundingClientRect()
  return sentinelRect.top < scrollRect.bottom && sentinelRect.bottom > scrollRect.top
}
```

- 创建 observer 后必须调用 **`observer.observe(sentinelRef.value)`**，否则滚动不会触发加载。可传 `{ root: scrollRef.value, rootMargin: '2px', threshold: 0 }`，使“进入滚动区域顶部”时触发。
- 在 **onBeforeUnmount** 中执行 `observer?.disconnect()`，避免内存泄漏。

---

## 5. 添加系统提示词和短期记忆（多轮对话）

### 5.1 创建 SystemPrompt 模型

在 `AIFriends/backend/web/models/friend.py` 中创建 **SystemPrompt** 模型，用于存储所有 agent 的系统提示词（存库后修改更方便，无需改代码重启）。

字段示例：`title`、`order_number`（或 `old_number`，用于排序）、`prompt`、`create_time`、`update_time`。

参考提示词可参考课程提供的链接，将内容按条写入数据库（如 title='回复'、'记忆' 等）。

### 5.2 系统提示词与最近 10 条对话

在 **chat.py** 中：

- 实现 `add_system_prompt(state, friend)`：从 `SystemPrompt.objects.filter(title='回复').order_by('order_number')`（若模型字段为 `old_number` 则用 `order_by('old_number')`）拼出 prompt，加上 `【角色性格】\n{friend.character.profile}`，返回 `{'messages': [SystemMessage(prompt)] + state['messages']}`。
- 实现 `add_recent_message(state, friend)`（或 `add_recent_messages`）：从 `Message.objects.filter(friend=friend).order_by('-id')[:10]` 取最近 10 条，转为 list 后 reverse，按条拼成 `HumanMessage` / `AIMessage`，再与当前 `state['messages']` 组合（如 `msgs[:1] + history + msgs[1:]` 或 `msgs[:1] + history + msgs[-1:]`），注意用 **list(...)** 再 **.reverse()**，不能对切片后的 QuerySet 直接 `.reverse()`）。
- 在 `post` 中先 `add_system_prompt(inputs, friend)`，再 `add_recent_message(inputs, friend)`，再传入 `event_stream` / `app.stream`。

---

## 6. 添加 Function Call

在 **chat/graph.py** 中：

- 从 `langchain_core.tools` 导入 **`tool`**（不要从 `json` 等错误位置导入）。
- 定义带文档字符串的工具，例如：

```python
@tool
def get_time() -> str:
    """当需要查询精确时间时，调用此函数。返回格式为：[年-月-日 时:分:秒]"""
    return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')

tools = [get_time]
```

- `ChatOpenAI(...).bind_tools(tools)`。
- 定义 **ToolNode(tools)** 与 **should_continue(state)**：取 `state['messages'][-1]`，若 `last_message.tool_calls` 则返回 `"tools"`，否则 `"end"`。
- 使用 **add_conditional_edges** 在 `'agent'` 与 `'tools'` 之间分支，并 `graph.add_edge('tools', 'agent')` 形成循环。

---

## 7. 添加长期记忆

- 在 **系统提示词**（add_system_prompt）中追加：`【长期记忆】\n{friend.memory}\n`（Friend 模型需有 `memory` 字段）。
- 新建 **memory 模块**：
  - **memory/update.py**：定义 **MemoryGraph**（与 chat 图类似，状态用 `messages`，单节点 LLM，`model_call` 中 `llm.invoke(state['messages'])`，返回 `{'messages': [res]}`）。
  - **memory/graph.py**（或按你项目命名）：实现 **update_memory(friend)**；内部 `create_system_message()` 从 `SystemPrompt.objects.filter(title='记忆').order_by('old_number')` 拼 prompt，`create_human_message(friend)` 用 `friend.memory` 与最近 10 条 Message 拼成 HumanMessage；`app = MemoryGraph.create_app()`，`res = app.invoke({'messages': [create_system_message(), create_human_message(friend)]})`，然后 `friend.memory = res['messages'][-1].content[:5000]`，`friend.update_time = now()`，`friend.save()`。
- 在 **chat.py** 的 `event_stream()` 里，在 **Message.objects.create(...)** 之后调用 **update_memory(friend)**（可按 demo 用 `Message.objects.filter(friend=friend).count() % 1 == 0` 控制频率，实现“每轮都更新”）。

---

## 8. 知识库

### 8.1 向量数据库 LanceDB

安装：`pip install lancedb langchain-community`（按需加 `tantivy`）。可参考 [LanceDB 文档](https://docs.lancedb.com/quickstart)。

### 8.2 Embedding 模型

在 `AIFriends/backend/web/documents/utils/custom_embeddings.py` 中实现 **CustomEmbeddings**：

- 从 **`langchain_core.embeddings`** 导入 **Embeddings**（不要从 `langchain_core` 直接 import Embeddings）。
- 使用 `OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("API_BASE"))`，在 `embed_documents` 中按 batch 调用 `client.embeddings.create(model="text-embedding-v4", input=batch, dimensions=1024)`，在 `embed_query` 中复用 `embed_documents([text])[0]`。

### 8.3 插入文档

- 在 `.gitignore` 中加入 `backend/web/documents/`（避免把文档数据提交）。若已索引可 `git rm --cached -f backend/web/documents/ -r`。
- 在 `documents/utils/insert_documents.py` 中：使用 **TextLoader** 加载 `./web/documents/data.txt`（**encoding='utf-8'**，注意拼写），**RecursiveCharacterTextSplitter** 切分，**LanceDB.from_documents(..., embedding=..., connection=db, table_name='my_knowledge_base', mode='overwrite')**；需 **from langchain_community.vectorstores import LanceDB**。
- 在 REPL 或脚本中直接运行 `insert_documents()` 时，需在函数开头 **load_dotenv()**，并保证当前工作目录为 **backend**，否则 `API_KEY` 为空会报错。

### 8.4 查询知识库的 Tool

在 **chat/graph.py** 中增加工具：

- 导入 **lancedb**、**LanceDB**（langchain_community.vectorstores）、**CustomEmbeddings**。
- `@tool` 定义 **search_knowledge_base(query: str)**，内部 `lancedb.connect(...)`、`CustomEmbeddings()`、`LanceDB(connection=db, embedding=embeddings, table_name='my_knowledge_base')`，`similarity_search(query, k=3)`，将结果拼成字符串返回；**join 时使用列表推导**：`'\n\n'.join([f'内容片段：{i+1}\n{doc.page_content}' for i, doc in enumerate(docs)])`。
- 将 `search_knowledge_base` 加入 **tools** 列表，与 get_time 一起传给 **bind_tools** 和 **ToolNode**。

---

## 9. 打包代码

- 删除调试信息（如 `print`、`pprint` 等）。
- 前端 **Message** 组件聊天气泡加上 **break-all**，避免英文过长撑出聊天区域。
- 将前端构建产物打包到后端（如 `npm run build` 后输出到 `backend/static/frontend/` 并更新 `backend/web/templates/index.html`）。

---

## 小结

| 模块           | 后端 | 前端 |
|----------------|------|------|
| 聊天发送与流式 | Message 模型；chat/graph（StateGraph、streaming、include_usage）；chat.py（event_stream、SSERenderer、Message.objects.create）；urls | streamApi.js（fetchEventSource、401 刷新重试）；InputField 用 streamApi、pushBackMessage（user + 空 ai）、addToLastMessage、isProcessing |
| 聊天记录       | get_history（last_message_id、friend_id、分页 10 条）；urls | ChatField（history、ref chat-history-ref、handlePushBackMessage/AddToLastMessage/PushFrontMessage、resolveMediaUrl 背景）；ChatHistory（loadMore、lastMessageId、observer.observe、scroll 位置保持、onBeforeUnmount）；Message（:src、resolveMediaUrl、whitespace-pre-wrap） |
| 系统提示与多轮 | SystemPrompt 模型；add_system_prompt、add_recent_message（最近 10 条，list+reverse）；chat 中组合 inputs | — |
| Function Call  | @tool（langchain_core.tools）；get_time；bind_tools、ToolNode、should_continue、conditional_edges | — |
| 长期记忆       | friend.memory；memory/update（MemoryGraph）、memory/graph（update_memory、create_system_message、create_human_message）；chat 中【长期记忆】+ 每轮后 update_memory | — |
| 知识库         | lancedb、LanceDB；CustomEmbeddings（Embeddings 从 langchain_core.embeddings 导入）；insert_documents（load_dotenv、encoding、LanceDB.from_documents）；search_knowledge_base tool | — |
| 打包           | — | break-all；npm run build → 后端静态与 index.html |

**路由汇总（本节涉及）**：

- `api/friend/message/chat/`
- `api/friend/message/get_history/`

**易错点**：`handlePushFrontMessage` 用 **unshift** 不是 shift；传给 ChatHistory 的是 **friend.character** 不是 friend.history；InputField 第二条 pushBackMessage 的 AI 条 **content 为 ''**；ChatHistory 必须 **observer.observe(sentinelRef.value)** 且变量名 **lastMessageId** 与请求参数一致；Message 头像用 **:src** 和 **resolveMediaUrl**；流式请求失败时在 **catch** 里也要 **isProcessing = false**；add_recent_message 中 QuerySet 切片后先 **list(...)** 再 **.reverse()**；**@tool** 从 **langchain_core.tools** 导入；Embeddings 从 **langchain_core.embeddings** 导入；insert_documents 在函数内 **load_dotenv()** 且需在 **backend** 目录下运行；search_knowledge_base 中 **join** 使用 **列表** `'\n\n'.join([...])`。
