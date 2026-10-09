## Lesson 6：语音模块

---

## 上节课的补丁

- **修复聊天框空消息后无法再发送的问题**：
  - 在 `InputField.vue` 中，`handleSend` 会先 `trim()` 内容并在为空时直接 `return`，不会推进 `processId` 或推空消息到 history。
  - 只有当内容非空时才会自增 `processId`、推入 user/ai 消息和发起流式请求，因此聊天框一开始为空时按回车 / 点发送不会破坏后续的发送逻辑。

- **聊天框用 ESC 关闭时也要调用 handleClose 逻辑**：
  - 用 ESC 关闭 `<dialog>` 时，浏览器只会关闭弹窗，不会执行我们写的关闭按钮里的 `handleClose()`，导致输入框状态（麦克风面板、语音播放等）没有重置。
  - 在 `ChatField.vue` 中给 `<dialog>` 绑定 `@close="onDialogClose"`，在 `onDialogClose()` 里调用 `inputRef.value?.close?.()`，这样无论是点击 ✕ 还是按 ESC 关闭，都会执行 `InputField` 的 `close()`（停止语音、收起麦克风）。

---

## 1. 前端实现语音输入

### 1.1 实现消息打断（防止旧回复“干扰”）

在 `InputField.vue` 中，我们用一个自增的 `processId` 来标记“这一次发送”的会话编号：

- 每次发送文字或语音消息时，都会执行：

```js
const curId = ++processId
```

- SSE 流式回调中，会优先判断：

```js
if (curId !== processId) return
```

这意味着：

- 新消息发送时，`processId` 自增，旧请求中的 `curId` 就不再等于当前的 `processId`。
- 旧请求后面流回来的内容会被直接 `return` 丢弃，不会再追加到当前最新那条 AI 消息上。

**效果**：当用户在 AI 还没说完时重新发送一条消息，旧回复会被自动打断，前端只会展示最新一个问题的答案。

此外，为了配合语音播放：

- `close()` / `handleStop()` 中都会先 `++processId` 再 `stopAudio()`，确保停止播放时也会打断还在流式返回中的内容。

---

### 1.2 安装语音识别相关包与静态资源

在 `frontend/package.json` 中，我们已经加入了：

```json
"dependencies": {
  "@ricky0123/vad-web": "^0.0.30",
  ...
}
```

安装：

```bash
cd AIFriends/frontend
npm install
```

`@ricky0123/vad-web` 会从 npm 下载人声检测与 ONNX 运行时的模型文件，安装过程可能稍慢，需要耐心等待。

为了让浏览器能从本地加载 VAD 模型，需要把相关静态文件拷贝到 `frontend/public/vad/` 目录：

- 从 `frontend/node_modules/@ricky0123/vad-web/dist/` 复制：
  - `silero_vad_legacy.onnx`
  - `vad.worklet.bundle.min.js`
- 从 `frontend/node_modules/onnxruntime-web/dist/` 复制：
  - 所有 `*.wasm` 文件
  - `ort-wasm-simd-threaded.mjs`

并在仓库根目录的 `.gitignore` 中忽略该目录：

```gitignore
frontend/public/vad/
```

如果之前已经被 git 索引：

```bash
git rm --cached -f frontend/public/vad -r
```

刷新页面后，前端即可从 `http://localhost:5173/vad/`（开发环境）加载这些模型文件。

---

### 1.3 麦克风组件与文字/语音切换

#### 1.3.1 `InputField.vue`：切换逻辑与打断语音

位置：`frontend/src/components/character/chat_field/input_field/InputField.vue`

关键状态与方法：

- `showMic = ref(false)`：控制当前是文字输入（false）还是语音输入（true）。
- `openMic()` / `closeMic()`：切换 `showMic`；`close()` 在关闭聊天框时会调用 `closeMic()` 并顺便打断当前语音播放。  
- `processId`：每次发送消息、停止语音时都会 `++processId`，配合 SSE 回调中的 `curId !== processId` 实现消息打断。

模板结构：

```vue
<form v-if="!showMic" @submit.prevent="handleSend" ...>
  <!-- 文本输入框 + 发送按钮 + 麦克风图标 -->
</form>
<Microphone
  v-else
  @close="closeMic"
  @send="handleSend"
  @stop="handleStop"
/>
```

当用户点击麦克风图标时：

- `openMic()` 把 `showMic` 设为 `true`，隐藏文字输入框，显示麦克风组件。

当用户点击键盘图标或关闭聊天框时：

- `closeMic()` 把 `showMic` 设为 `false`，恢复文字输入模式；
- `close()` 还会 `++processId` 与 `stopAudio()`，确保打断当前语音流与 TTS 播放。

#### 1.3.2 `Microphone.vue`：组件结构与 UI

位置：`frontend/src/components/character/chat_field/input_field/Microphone.vue`

组件 props/emits：

- 不接收 props；通过 `emit` 向父组件发送事件：  
  - `close`：用户点击键盘图标，表示切回文字输入。  
  - `send`：ASR 成功识别出文本后发送给父组件。  
  - `stop`：开始新一轮录音时通知父组件停止当前回复（打断旧消息）。

模板：

```vue
<div class="absolute bottom-4 left-2 h-12 w-86 flex items-center bg-black/30 backdrop-blur-sm rounded-2xl">
  <div v-if="isSpeaking" class="flex items-center justify-center gap-1 h-6 flex-1">
    <div
      v-for="i in 32" :key="i"
      class="w-0.5 bg-blue-400 rounded-full animate-wave"
      :style="{ animationDelay: `${i * 0.1}s` }"
    ></div>
  </div>
  <div v-else class="text-white/50 text-base w-full text-center">
    语音输入
  </div>
  <div @click="emit('close')" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer">
    <KeyboardIcon />
  </div>
</div>
```

配合样式：

```vue
<style scoped>
.animate-wave {
  height: 4px;
  animation: wave-animation 0.6s ease-in-out infinite alternate;
}
@keyframes wave-animation {
  0% { height: 4px; opacity: 0.3; }
  100% { height: 20px; opacity: 1; }
}
</style>
```

`isSpeaking` 为 `true` 时显示波浪条，为 `false` 时显示“语音输入”文字，且键盘图标始终在右侧，视觉上与文字输入框保持一致。

---

### 1.4 引入 VAD 包并检测人声

在 `Microphone.vue` 中：

```js
import { MicVAD } from '@ricky0123/vad-web';
import KeyboardIcon from '../../icon/KeyboardIcon.vue';
import { onBeforeUnmount, onMounted, ref } from 'vue';
import api from '@/js/http/api';

const emit = defineEmits(['close', 'send', 'stop'])
const isSpeaking = ref()

let vadInstance = null;

const startRecording = async () => {
  const baseUrl = "http://localhost:5173/vad/";
  try {
    vadInstance = await MicVAD.new({
      baseAssetPath: baseUrl,
      onSpeechStart: () => {
        isSpeaking.value = true;
        emit('stop')          // 通知父组件打断当前回复
      },
      onSpeechEnd: (audio) => {
        isSpeaking.value = false;
        const pcm16 = float32ToInt16(audio);
        sendToBackend(pcm16); // 发送到后端做 ASR
      },
      ortConfig: (ort) => {
        ort.env.wasm.wasmPaths = baseUrl;
        ort.env.logLevel = "error";
      },
      positiveSpeechThreshold: 0.8,
      negativeSpeechThreshold: 0.65,
      minSpeechFrames: 5,
      redemptionFrames: 5,
    });

    await vadInstance.start();
  } catch (e) {
    console.error("VAD 初始化失败:", e);
  }
};
```

`MicVAD` 会自动：

- 监听麦克风音频流；
- 区分人声与环境噪音；
- 在检测到一段连续的人声结束时，调用 `onSpeechEnd(audio)`，并传入这段音频的 `Float32Array`。

将 `Float32` 转为 16-bit PCM：

```js
const float32ToInt16 = (float32Array) => {
  const buffer = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    buffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return buffer.buffer;
};
```

生命周期管理：

```js
onMounted(() => {
  startRecording()
})

onBeforeUnmount(() => {
  if (vadInstance) {
    vadInstance.destroy()
    vadInstance = null
  }
})
```

---

### 1.5 定义 `send` 与 `stop` 事件

`Microphone.vue` 通过 `emit` 与 `InputField` 通信：

- **`stop`**：在 `onSpeechStart` 触发，表示开始一段新的语音输入。
  - `InputField` 中的 `handleStop`：

    ```js
    function handleStop() {
      ++processId
      stopAudio()
    }
    ```

  - 作用：打断当前 SSE 回复和音频播放（见 4 节）。

- **`send`**：在 ASR 识别成功后触发：

  ```js
  if (data.result === 'success') {
    emit('send', null, data.text)
  }
  ```

  `InputField` 中的 `handleSend(event, audio_msg)` 会接收 `audio_msg`，用它作为文本内容重新走一遍“发送消息 → 流式回复 → 语音合成”的全流程。

---

### 1.6 将语音发送到后端

`Microphone.vue` 中的 `sendToBackend` 实现了把音频发送到 Django 后端的 ASR 接口：

```js
const sendToBackend = async (arrayBuffer) => {
  const blob = new Blob([arrayBuffer], {type: "audio/pcm"});
  const formData = new FormData();
  formData.append("audio", blob, 'voice.pcm')

  try {
    const res = await api.post('/api/friend/message/asr/asr/', formData)
    const data = res.data
    if (data.result === 'success') {
      emit('send', null, data.text)
    }
  } catch (err) {
    console.log(err)
  }
};
```

注意：

- `api` 使用了 `BASE_URL = 'http://127.0.0.1:8000'`（开发环境），因此完整 URL 为 `http://127.0.0.1:8000/api/friend/message/asr/asr/`。
- ASR 接口返回 `{'result': 'success', 'text': '识别出的文本'}`，前端拿到 `text` 后通过 `emit('send', null, data.text)` 交给 `InputField`。

---

## 2. 后端实现语音识别（ASR）

阿里云实时语音识别（ASR）文档可参考百炼平台；在本项目中，我们使用 websockets 连接阿里云的 `gummy-realtime-v1` 模型。

### 2.1 安装依赖

在 `backend` 中安装：

```bash
cd AIFriends/backend
pip install websockets
```

（`basedpyright` 会对 `import websockets` 给出“could not be resolved”警告，只要 pip 已安装实际运行不会有问题。）

### 2.2 `ASRView` 实现

位置：`backend/web/views/friend/message/asr/asr.py`

核心代码结构：

```python
import asyncio
import json
import os
import uuid

import websockets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class ASRView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'result': '音频不存在'})
        pcm_data = audio.read()
        text = asyncio.run(self.run_asr_tasks(pcm_data))
        return Response({'result': 'success', 'text': text})
```

其中 `run_asr_tasks` 使用 websockets 连接阿里云实时语音识别服务：

```python
    async def asr_sender(self, pcm_data, ws, task_id):
        chunk = 3200
        for i in range(0, len(pcm_data), chunk):
            await ws.send(pcm_data[i: i + chunk])
            await asyncio.sleep(0.01)
        await ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {"input": {}}
        }))

    async def asr_receiver(self, ws):
        text = ''
        async for msg in ws:
            data = json.loads(msg)
            event = data['header']['event']
            if event == 'result-generated':
                output = data['payload']['output']
                if output.get('transcription', None) and output['transcription']['sentence_end']:
                    text += output['transcription']['text']
            elif event in ['task-finished', 'task-failed']:
                break
        return text

    async def run_asr_tasks(self, pcm_data):
        task_id = uuid.uuid4().hex
        api_key = os.getenv('API_KEY')
        wss_url = os.getenv('WSS_URL')
        headers = {"Authorization": f"Bearer {api_key}"}
        async with websockets.connect(wss_url, additional_headers=headers) as ws:
            await ws.send(json.dumps({
                "header": {
                    "streaming": "duplex",
                    "task_id": task_id,
                    "action": "run-task"
                },
                "payload": {
                    "model": "gummy-realtime-v1",
                    "parameters": {
                        "sample_rate": 16000,
                        "format": "pcm",
                        "transcription_enabled": True,
                    },
                    "input": {},
                    "task": "asr",
                    "task_group": "audio",
                    "function": "recognition"
                }
            }))
            async for msg in ws:
                if json.loads(msg)['header']['event'] == 'task-started':
                    break
            _, text = await asyncio.gather(
                self.asr_sender(pcm_data, ws, task_id),
                self.asr_receiver(ws),
            )
            return text
```

环境变量：

- `API_KEY`：阿里云百炼平台的 API Key（已在 `.env` 中配置）。
- `WSS_URL`：阿里云实时语音识别模型的 websocket 地址。

### 2.3 路由配置

在 `backend/web/urls.py` 中：

```python
from .views.friend.message.asr.asr import ASRView
...
path('api/friend/message/asr/asr/', ASRView.as_view()),
```

这样前端请求 `/api/friend/message/asr/asr/` 就能命中 ASRView。

---

## 3. 后端实现语音合成（TTS）与 SSE

### 3.1 TTS 与多线程队列

在 `backend/web/views/friend/message/chat/chat.py` 中，我们在原有文字聊天 SSE 基础上，引入了阿里云 TTS：

- 使用 `threading.Thread` 启动一个后台线程，负责：
  - 调用 LangGraph 的 `app.astream` 流式获取大模型文本；
  - 通过 websocket 调用阿里云 TTS 服务，将文本转换为音频流；
  - 把文本片段、音频片段、usage 信息写入线程安全队列 `queue.Queue()`。
- 主线程通过 **Server-Sent Events (SSE)**：
  - 不断从队列中读取消息；
  - 对文本片段写入 `data: {"content": "..."}\n\n`；
  - 对音频片段写入 `data: {"audio": "<base64>"}\n\n`；
  - 最后写入 `data: [DONE]\n\n`。

这部分代码已经和 demo 的 `chat.py` 保持一致，不再赘述，详细可参考 Lesson 5 中对 `event_stream` 的讲解，这一节重点是“怎么利用这些 `audio` 字段在前端播放语音”。

---

## 4. 前端播放语音回复

`InputField.vue` 中实现了一个简单的“流式音频播放器”，基于浏览器的 **MediaSource Extensions (MSE)**：

```js
let mediaSource = null;
let sourceBuffer = null;
let audioPlayer = new Audio(); // 全局播放器实例
let audioQueue = [];           // 待写入 Buffer 的二进制队列
let isUpdating = false;        // Buffer 是否正在写入
```

### 4.1 初始化音频流

```js
const initAudioStream = () => {
  audioPlayer.pause();
  audioQueue = [];
  isUpdating = false;

  mediaSource = new MediaSource();
  audioPlayer.src = URL.createObjectURL(mediaSource);

  mediaSource.addEventListener('sourceopen', () => {
    try {
      sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
      sourceBuffer.addEventListener('updateend', () => {
        isUpdating = false;
        processQueue();
      });
    } catch (e) {
      console.error("MSE AddSourceBuffer Error:", e);
    }
  });

  audioPlayer.play().catch(e => console.error("等待用户交互以播放音频"));
};
```

在每次发送消息（文字或语音）前，我们会先调用 `initAudioStream()`，清空队列并重新建立 `MediaSource`，避免不同轮次的语音混在一起。

### 4.2 处理流式音频片段

`handleAudioChunk` 用于接收后端 SSE 中的 `audio` 片段（base64 编码）：

```js
const handleAudioChunk = (base64Data) => {
  try {
    const binaryString = atob(base64Data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    audioQueue.push(bytes);
    processQueue();
  } catch (e) {
    console.error("Base64 Decode Error:", e);
  }
};
```

`processQueue` 会逐块写入 `SourceBuffer`：

```js
const processQueue = () => {
  if (isUpdating || audioQueue.length === 0 || !sourceBuffer || sourceBuffer.updating) {
    return;
  }
  isUpdating = true;
  const chunk = audioQueue.shift();
  try {
    sourceBuffer.appendBuffer(chunk);
  } catch (e) {
    console.error("SourceBuffer Append Error:", e);
    isUpdating = false;
  }
};
```

在 SSE 回调中，如果 `data.audio` 存在，就调用 `handleAudioChunk(data.audio)`：

```js
onmessage(data, isDone) {
  if (curId !== processId) return

  if (data.content) {
    emit('addToLastMessage', data.content)
  }
  if (data.audio) {
    handleAudioChunk(data.audio)
  }
}
```

### 4.3 停止播放与组件卸载

`stopAudio` 负责彻底停止并释放资源：

```js
const stopAudio = () => {
  audioPlayer.pause();
  audioQueue = [];
  isUpdating = false;

  if (mediaSource) {
    if (mediaSource.readyState === 'open') {
      try {
        mediaSource.endOfStream();
      } catch (e) {}
    }
    mediaSource = null;
  }
  if (audioPlayer.src) {
    URL.revokeObjectURL(audioPlayer.src);
    audioPlayer.src = '';
  }
};
```

在以下场景中会调用它：

- `handleStop()`：当麦克风开始新一轮录音时（`emit('stop')`），停止旧的语音播放。
- `close()`：当关闭聊天框或切回文字输入时，既会 `++processId` 打断 SSE，又会停止音频播放。
- `onUnmounted`：组件卸载时，暂停播放器并清空 `src`，避免内存泄漏。

---

## 5. 打包与部署时的特别注意

在开发环境中：

- ASR 与聊天接口都走 `http://127.0.0.1:8000/...`（由 `api.js` 的 `BASE_URL` 决定）；
- VAD 模型当前配置为 `http://localhost:5173/vad/`，即前端静态资源目录。

在将前端打包到后端时（`npm run build` → 拷贝到 `backend/static/frontend/`）：

- 推荐将 `Microphone.vue` 中的 `baseUrl` 改成与 demo 一致：

```python
const baseUrl = "http://127.0.0.1:8000/static/frontend/vad/";
```

- 并把 `frontend/public/vad` 目录同步到后端的 `static/frontend/vad/` 中。这样无论开发还是部署，VAD 模型都统一由后端静态服务提供。

部署前请确保：

- 删除多余的 `console.log`、调试代码；
- 前后端的 URL、端口与静态资源路径保持一致。

---

## 小结

- **语音输入**：通过 `MicVAD` 自动检测人声，录完一段话后转换为 16-bit PCM，上传到后端 ASR 接口获取文本，再走与文字输入相同的聊天流程。
- **消息打断**：利用 `processId` 和 `stop` 事件，确保每次新消息或新一轮语音开始时，旧的文本回复与语音播放都会被安全打断。
- **语音合成与播放**：后端用阿里云 TTS 生成 mp3 音频，通过 SSE 以 base64 字符串流式返回；前端用 MSE（MediaSource + SourceBuffer）实现边下边播的语音体验。
- **配置与打包**：注意本地与部署环境下 `BASE_URL`、`WSS_URL` 和 VAD 模型静态路径的一致性，将 `frontend/public/vad` 加入 `.gitignore` 以避免模型文件被提交到仓库。

