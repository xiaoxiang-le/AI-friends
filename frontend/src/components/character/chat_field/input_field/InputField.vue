<script setup>
import SendIcon from "@/components/character/icons/SendIcon.vue";
import MicIcon from "@/components/character/icons/MicIcon.vue";
import {onUnmounted, ref, useTemplateRef} from "vue";
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
const enableAudio = ref(false)
let requestId = null
let lastContent = ''
let lastFailed = false

async function openMicrophone() {
  errorMessage.value = ''
  try {
    const {data} = await api.get('/api/capabilities/')
    if (!data.capabilities.asr.configured) {
      errorMessage.value = '语音识别暂不可用，请联系管理员或使用文字输入'
      return
    }
    showMic.value = true
  } catch {
    errorMessage.value = '暂时无法开启语音输入，请稍后重试'
  }
}

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
  <div v-if="errorMessage" class="chat-error flex items-center gap-2" role="alert">
    <span class="flex-1">{{ errorMessage }}</span>
    <button type="button" aria-label="关闭提示" @click="errorMessage = ''">×</button>
  </div>
  <label class="text-sm px-3 flex items-center gap-2">
    <input type="checkbox" v-model="enableAudio" :disabled="sending" aria-label="语音播报">朗读回复
  </label>
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
    <button type="button" aria-label="语音输入" :disabled="sending" @click="openMicrophone" class="absolute right-10 w-8 h-8 flex justify-center items-center cursor-pointer disabled:opacity-40">
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
