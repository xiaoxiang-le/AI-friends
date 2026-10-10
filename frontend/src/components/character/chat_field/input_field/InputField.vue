<script setup>
import SendIcon from "@/components/character/icons/SendIcon.vue";
import MicIcon from "@/components/character/icons/MicIcon.vue";
import {computed, onUnmounted, ref, useTemplateRef} from "vue";
import api from '@/js/http/api.js';
import streamApi from "@/js/http/streamApi.js";
import Microphone from "@/components/character/chat_field/input_field/Microphone.vue";

const props = defineProps(['friendId'])
const emit = defineEmits(['pushBackMessage', 'addToLastMessage', 'setMessageState', 'setMessageAudio', 'setMessageMeta', 'replaceFailed'])
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

let audioChunks = []
const audioUrls = new Set()
const canSend = computed(() => !!message.value.trim())

function stopAudio() {
  audioChunks = []
  document.querySelectorAll('audio[data-chat-voice]').forEach(player => player.pause())
}
function handleAudioChunk(base64Data) {
  audioChunks.push(Uint8Array.from(atob(base64Data), character => character.charCodeAt(0)))
}
function completeAudio() {
  if (!audioChunks.length) return
  const url = URL.createObjectURL(new Blob(audioChunks, {type: 'audio/mpeg'}))
  audioUrls.add(url)
  audioChunks = []
  emit('setMessageAudio', url)
}
function handlePrimaryAction() {
  if (sending.value) handleStop()
  else handleSend()
}

onUnmounted(() => {
    handleStop();
    stopAudio();
    audioUrls.forEach(url => URL.revokeObjectURL(url));
});

function focus() {
  inputRef.value?.focus()
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
  stopAudio()

  const curId = ++ processId
  message.value = ''
  const retryId = lastFailed && content === lastContent ? requestId : null
  if(retryId) emit('replaceFailed')
  lastContent = content
  requestId = retryId || crypto.randomUUID()
  lastFailed = false

  emit('pushBackMessage', {role: 'user', content: content, id: crypto.randomUUID()})
  emit('pushBackMessage', {role: 'ai', content: '', state: 'streaming', voiceRequested: enableAudio.value, id: crypto.randomUUID()})

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
          completeAudio()
        }
        if (data.message_id) emit('setMessageMeta',data)
        if (data.warning) {errorMessage.value = data.warning; audioChunks=[]}

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
  <div class="composer-toolbar">
    <button type="button" role="switch" :aria-checked="enableAudio" aria-label="角色语音回复"
      :disabled="sending" class="voice-toggle" :class="{'is-on': enableAudio}" @click="enableAudio = !enableAudio">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></svg>
      <span>角色语音回复</span><span class="switch-track"><span /></span>
    </button>
    <span v-if="sending" class="generating-status" role="status"><i />正在回复</span>
  </div>
  <p v-if="lastFailed" class="text-sm px-3">发送内容已恢复，可编辑后重试</p>
  <form v-if="!showMic" @submit.prevent="handlePrimaryAction" class="chat-input composer">
    <button type="button" aria-label="语音输入" :disabled="sending" @click="openMicrophone" class="mic-action"><MicIcon /></button>
    <input ref="input-ref" v-model="message" class="composer-text" type="text"
      :placeholder="sending ? '角色正在回复…' : '发消息…'" aria-label="聊天消息" maxlength="10000" :disabled="sending">
    <button type="submit" :aria-label="sending ? '停止回复' : '发送消息'" :title="sending ? '点击停止回复' : '发送消息'"
      :disabled="!sending && !canSend" :aria-busy="sending" class="send-action" :class="{'is-generating': sending}">
      <span v-if="sending" class="stop-square" aria-hidden="true" /><SendIcon v-else />
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
.composer-toolbar {display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 3px 7px;flex-shrink:0}
.voice-toggle {display:flex;align-items:center;gap:7px;border:0;background:rgba(255,255,255,.92);color:#64716a;border-radius:20px;padding:7px 11px;font-size:12px;cursor:pointer;box-shadow:0 1px 4px #0000000d}
.voice-toggle svg {width:16px;height:16px}.voice-toggle.is-on {color:#087d45}.voice-toggle:disabled {cursor:default}
.switch-track {width:27px;height:16px;border-radius:10px;background:#c8ceca;padding:2px;transition:background .2s}
.switch-track span {display:block;width:12px;height:12px;border-radius:50%;background:white;transition:transform .2s}
.is-on .switch-track {background:#07c160}.is-on .switch-track span {transform:translateX(11px)}
.generating-status {display:flex;align-items:center;gap:6px;font-size:12px;color:#fff;text-shadow:0 1px 4px #0008;padding-right:5px}
.generating-status i {width:6px;height:6px;background:#9af2bb;border-radius:50%;animation:pulse 1.2s infinite}
.composer {height:54px;gap:8px;padding:6px;background:rgba(255,255,255,.96);border:1px solid #ffffff88;border-radius:18px;box-shadow:0 3px 15px #00000012}
.composer-text {min-width:0;flex:1;height:100%;background:transparent;border:0;outline:0;color:#203329;font-size:15px}.composer-text::placeholder {color:#9aa59e}
.mic-action {width:34px;height:38px;display:grid;place-items:center;color:#53665a;border:0;background:transparent;border-radius:12px;cursor:pointer}.mic-action:disabled {opacity:.4}
.send-action {width:40px;height:40px;flex-shrink:0;display:grid;place-items:center;border:0;border-radius:13px;background:#07c160;color:white;cursor:pointer;transition:background .15s,transform .15s}
.send-action:disabled {background:#e8eee9;color:#acb8af;cursor:default}.send-action:hover:not(:disabled) {background:#06a953}.send-action:active:not(:disabled) {transform:scale(.94)}
.send-action.is-generating {background:#e4f8ec;color:#07974c;position:relative}.send-action.is-generating::before {content:'';position:absolute;inset:4px;border:2px solid #08a45122;border-top-color:#08a451;border-radius:10px;animation:spin 1.4s linear infinite}
.stop-square {width:12px;height:12px;background:currentColor;border-radius:3px}
.send-action :deep(svg) {width:21px;height:21px;color:inherit}.mic-action :deep(svg) {width:21px;height:21px;color:inherit}
button:focus-visible {outline:2px solid #08a451;outline-offset:3px}.composer:focus-within {border-color:#9ad8b1}
@keyframes spin {to {transform:rotate(360deg)}}@keyframes pulse {50% {opacity:.35}}
@media(prefers-reduced-motion:reduce) {.send-action.is-generating::before,.generating-status i {animation:none}}
</style>
