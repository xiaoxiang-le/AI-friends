<script setup>
import SendIcon from "@/components/character/icons/SendIcon.vue";
import MicIcon from "@/components/character/icons/MicIcon.vue";
import {onMounted, onUnmounted, ref, useTemplateRef} from "vue";
import api from '@/js/http/api.js';
import streamApi from "@/js/http/streamApi.js";
import Microphone from "@/components/character/chat_field/input_field/Microphone.vue";

const props = defineProps(['friendId'])
const emit = defineEmits(['pushBackMessage', 'addToLastMessage', 'setMessageState'])
const inputRef = useTemplateRef('input-ref')
const message = ref('')
const sending = ref(false)
const errorMessage = ref('')
let controller = null
let processId = 0
const showMic = ref(false)
const capabilities = ref(null)
const enableAudio = ref(false)
const capabilityError = ref('')
let requestId = null
let lastContent = ''
let lastFailed = false
onMounted(async () => {
  try {
    capabilities.value = (await api.get('/api/capabilities/')).data.capabilities
  } catch {
    capabilityError.value = '无法读取服务状态，请刷新重试'
  }
})

let mediaSource = null;
let sourceBuffer = null;
let audioPlayer = new Audio(); // 全局播放器实例
let audioQueue = [];           // 待写入 Buffer 的二进制队列
let isUpdating = false;        // Buffer 是否正在写入
let audioComplete = false;

const initAudioStream = () => {
    stopAudio();
    if (!window.MediaSource || !MediaSource.isTypeSupported('audio/mpeg')) {
      errorMessage.value = '此浏览器暂不支持语音播报，可继续文字聊天';
      return;
    }
    audioQueue = [];
    isUpdating = false;
    audioComplete = false;

    mediaSource = new MediaSource();
    audioPlayer.src = URL.createObjectURL(mediaSource);

    mediaSource.addEventListener('sourceopen', () => {
        if (!mediaSource) return;
        try {
            sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
            sourceBuffer.addEventListener('updateend', () => {
                isUpdating = false;
                processQueue();
            });
            processQueue();
        } catch (e) {
            console.error("MSE AddSourceBuffer Error:", e);
        }
    });

    audioPlayer.play().catch(e => console.error("等待用户交互以播放音频"));
};

const processQueue = () => {
    if (audioQueue.length === 0 && audioComplete && mediaSource?.readyState === 'open' && sourceBuffer && !sourceBuffer.updating) {
        mediaSource.endOfStream();
        return;
    }
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

const stopAudio = () => {
    audioPlayer.pause();
    audioQueue = [];
    isUpdating = false;
    sourceBuffer = null;
    audioComplete = false;

    if (mediaSource) {
        if (mediaSource.readyState === 'open') {
            try {
                mediaSource.endOfStream();
            } catch (e) {
            }
        }
        mediaSource = null;
    }

    if (audioPlayer.src) {
        URL.revokeObjectURL(audioPlayer.src);
        audioPlayer.src = '';
    }
};

const handleAudioChunk = (base64Data) => {  // 将语音片段添加到播放器队列中
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

onUnmounted(() => {
    handleStop();
    stopAudio();
});

function focus() {
  inputRef.value.focus()
}

async function handleSend(event, audio_msg) {
  let content
  if (audio_msg) {
    content = audio_msg.trim()
  } else {
    content = message.value.trim()
  }
  if (!content) return

  if (sending.value) return
  if (!capabilities.value?.ai.configured) {
    errorMessage.value = 'AI 对话服务尚未配置，请联系管理员'
    return
  }
  sending.value = true
  errorMessage.value = ''
  controller = new AbortController()
  if (enableAudio.value) initAudioStream()

  const curId = ++ processId
  message.value = ''
  const retryId = lastFailed && content === lastContent ? requestId : null
  lastContent = content
  requestId = retryId || crypto.randomUUID()
  lastFailed = false

  emit('pushBackMessage', {role: 'user', content: content, id: crypto.randomUUID()})
  emit('pushBackMessage', {role: 'ai', content: '', state: 'streaming', id: crypto.randomUUID()})

  try {
    await streamApi('/api/friend/message/chat/', {
      signal: controller.signal,
      body: {
        friend_id: props.friendId,
        message: content,
        request_id: requestId,
        enable_audio: enableAudio.value,
      },
      onmessage(data, isDone) {
        if (curId !== processId) return
        if (isDone) {
          emit('setMessageState', 'completed')
          audioComplete = true
          processQueue()
        }
        if (data.warning) errorMessage.value = data.warning

        if (data.content) {
          emit('addToLastMessage', data.content)
        }
        if (data.audio) {
          handleAudioChunk(data.audio)
        }
      },
      onerror(err) {
        if (curId === processId) errorMessage.value = err.message || '发送失败，请重试'
      },
    })
  } catch (err) {
    if (curId === processId) {
      errorMessage.value = err.message || '发送失败，请重试'
      message.value = content
      lastFailed = true
      emit('setMessageState', 'failed')
      stopAudio()
    }
  } finally {
    if (curId === processId) sending.value = false
  }
}

function close() {
  handleStop()
  showMic.value = false
  stopAudio()
}

function handleStop() {
  if (sending.value && requestId) {
    api.post('/api/friend/message/cancel/', {request_id: requestId}).catch(() => {})
    emit('setMessageState', 'cancelled')
    message.value = lastContent
  }
  ++ processId
  controller?.abort()
  sending.value = false
  stopAudio()
}

defineExpose({
  focus,
  close,
})
</script>

<template>
  <div class="chat-service-status text-sm px-3 py-2 bg-white/90 rounded-lg">
    <span v-if="capabilityError" role="alert">{{ capabilityError }}</span>
    <span v-else-if="!capabilities">正在检查服务状态…</span>
    <span v-else-if="!capabilities.ai.configured">AI 服务未配置，暂不能生成回复</span>
    <span v-else>AI 已配置，实际可用性以请求结果为准</span>
    <label class="ml-3"><input type="checkbox" v-model="enableAudio" :disabled="sending || !capabilities?.tts.configured"> 语音播报</label>
    <span v-if="capabilities && !capabilities.asr.configured" class="ml-3">语音识别未配置</span>
  </div>
  <p v-if="errorMessage" class="chat-error" role="alert">{{ errorMessage }}</p>
  <button v-if="sending" type="button" class="btn btn-sm" @click="handleStop">停止生成</button>
  <p v-if="lastFailed" class="text-sm px-3">发送内容已恢复，可编辑后重试</p>
  <form v-if="!showMic" @submit.prevent="handleSend" class="chat-input">
    <input
        ref="input-ref"
        v-model="message"
        class="input bg-black/30 backdrop-blur-sm text-white text-base w-full h-full rounded-2xl pr-20"
        type="text"
        placeholder="文本输入..."
        aria-label="聊天消息"
        maxlength="10000"
        :disabled="sending"
    >
    <button type="submit" aria-label="发送消息" :disabled="sending" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer">
      <SendIcon />
    </button>
    <button type="button" aria-label="语音输入" :disabled="sending || !capabilities?.asr.configured" @click="showMic = true" class="absolute right-10 w-8 h-8 flex justify-center items-center cursor-pointer disabled:opacity-40">
      <MicIcon />
    </button>
  </form>
  <Microphone
      v-else
      @close="showMic = false"
      @send="(_, text) => {message = text; showMic = false}"
      @stop="handleStop"
  />
</template>

<style scoped>

</style>
