<script setup>
import {computed, ref, watch, nextTick, onMounted, onBeforeUnmount, useTemplateRef} from "vue";
import { useUserStore } from "@/stores/user.js";
import { resolveMediaUrl } from "@/js/http/api.js";

const props = defineProps(['message', 'character'])
const user = useUserStore()
const player = useTemplateRef('voice-player')
const playing = ref(false)
const duration = ref(0)
const voiceError = ref('')
const showTranscript = ref(false)
const showVoiceMenu = ref(false)
const voiceBlock = useTemplateRef('voice-block')
const textVisible = computed(() => !props.message.voiceRequested || showTranscript.value ||
  (!props.message.audioUrl && props.message.state !== 'streaming'))
function dismissVoiceMenu(event) {
  if (!voiceBlock.value?.contains(event.target)) showVoiceMenu.value = false
}
function convertToText() {
  showTranscript.value = true
  showVoiceMenu.value = false
}
onMounted(() => document.addEventListener('pointerdown', dismissVoiceMenu))
function pauseOtherVoices() {
  document.querySelectorAll('audio[data-chat-voice]').forEach(audio => {
    if (audio !== player.value) audio.pause()
  })
}
async function playVoice() {
  if (!player.value) return
  if (!player.value.paused) {player.value.pause(); return}
  pauseOtherVoices()
  if (player.value.ended) player.value.currentTime = 0
  try {await player.value.play(); voiceError.value = ''}
  catch {voiceError.value = '播放未能开始，请再点击语音重试'}
}
watch(() => props.message.audioUrl, async url => {
  if (!url) return
  await nextTick()
  pauseOtherVoices()
  try {await player.value?.play()}
  catch { /* Browser autoplay restrictions leave the bubble available for manual playback. */ }
}, {immediate:true})
onBeforeUnmount(() => {
  player.value?.pause()
  document.removeEventListener('pointerdown', dismissVoiceMenu)
})
</script>

<template>
  <div v-if="message.content || message.state">
    <div v-if="message.role === 'ai'" class="chat chat-start">
      <div class="chat-image avatar">
        <div class="w-10 rounded-full">
          <img :src="resolveMediaUrl(character?.photo)" alt="">
        </div>
      </div>
      <div class="ai-reply">
      <div v-if="textVisible" class="chat-bubble whitespace-pre-wrap break-all">{{ message.content || (message.state === 'streaming' ? '正在生成…' : '') }}
        <p v-if="message.state === 'failed'" class="text-xs">回复失败，内容尚未保存</p>
        <p v-if="message.state === 'cancelled'" class="text-xs">已停止，部分回复未保存</p>
      </div>
      <div v-if="message.voiceRequested && message.state === 'streaming' && !message.audioUrl" class="voice-pending" role="status">
        <span class="voice-waves" aria-hidden="true"><i /><i /><i /></span>正在准备语音…
      </div>
      <div v-if="message.audioUrl" ref="voice-block" class="voice-block" @contextmenu.prevent="showVoiceMenu = true"
        @keydown.esc.stop="showVoiceMenu = false">
      <button type="button" class="voice-bubble" :class="{'is-playing':playing}"
        :aria-label="playing ? '暂停角色语音' : '播放角色语音'" :aria-pressed="playing" @click="playVoice">
        <span class="voice-waves" aria-hidden="true"><i /><i /><i /></span>
        <span>{{ duration ? `${duration}″` : '语音回复' }}</span>
        <span class="voice-caption">{{ playing ? '播放中' : '点击播放' }}</span>
      </button>
      <button type="button" class="voice-more" aria-label="语音更多选项" :aria-expanded="showVoiceMenu"
        aria-haspopup="menu" @click="showVoiceMenu = !showVoiceMenu">⋯</button>
      <div v-if="showVoiceMenu" class="voice-menu" role="menu" aria-label="语音选项">
        <button v-if="!showTranscript" type="button" role="menuitem" @click="convertToText">语音转文字</button>
        <button v-else type="button" role="menuitem" @click="showTranscript = false; showVoiceMenu = false">收起文字</button>
      </div>
      </div>
      <audio v-if="message.audioUrl" ref="voice-player" data-chat-voice :src="message.audioUrl" preload="auto"
        @loadedmetadata="duration = Number.isFinite(player.duration) ? Math.ceil(player.duration) : 0"
        @play="playing = true" @pause="playing = false" @ended="playing = false"
        @error="voiceError = '语音播放失败，请重新发送消息'" />
      <p v-if="voiceError" class="voice-error" role="alert">{{ voiceError }}</p>
      </div>
    </div>
    <div v-else class="chat chat-end">
      <div class="chat-image avatar">
        <div class="w-10 rounded-full">
          <img :src="resolveMediaUrl(user.photo)" alt="">
        </div>
      </div>
      <div class="chat-bubble chat-bubble-success whitespace-pre-wrap">{{ message.content }}</div>
    </div>
  </div>
</template>


<style scoped>
.ai-reply {min-width:0;max-width:100%;display:flex;flex-direction:column;align-items:flex-start;gap:7px}
.ai-reply .chat-bubble {max-width:100%}
.voice-block {position:relative;display:flex;align-items:center;gap:4px;max-width:100%}
.voice-more {border:0;background:transparent;color:#6a8572;font-size:20px;cursor:pointer;padding:4px 7px;border-radius:8px}
.voice-more:hover {background:#ffffffb3}
.voice-menu {position:absolute;left:12px;bottom:calc(100% + 6px);min-width:132px;padding:5px;background:#fff;border:1px solid #e3e9e5;border-radius:10px;box-shadow:0 5px 22px #0002;z-index:5}
.voice-menu button {display:block;width:100%;border:0;background:transparent;text-align:left;padding:10px 13px;border-radius:7px;color:#28382d;font-size:13px;cursor:pointer}.voice-menu button:hover {background:#edf8f0}
.voice-pending {display:flex;align-items:center;gap:10px;background:#f6fff8;color:#799081;border-radius:4px 16px 16px 16px;padding:12px 15px;font-size:13px}
.voice-pending .voice-waves {opacity:.55;animation:wave 1s ease-in-out infinite alternate}
.voice-bubble {display:flex;align-items:center;gap:13px;min-width:152px;padding:12px 15px;border:1px solid #d8e8dc;border-radius:4px 16px 16px 16px;background:#f6fff8;color:#254832;font-size:15px;cursor:pointer;box-shadow:0 1px 3px #0000000a}
.voice-caption {font-size:11px;color:#8b9c90;margin-left:8px}.voice-bubble.is-playing {background:#dcf9e5;border-color:#9ce2b6}
.voice-waves {display:flex;align-items:center;gap:3px;height:22px}.voice-waves i {width:3px;border-radius:3px;background:#08a451;height:7px}.voice-waves i:nth-child(2) {height:13px}.voice-waves i:nth-child(3) {height:19px}
.is-playing .voice-waves i {animation:wave .8s ease-in-out infinite alternate}.is-playing .voice-waves i:nth-child(2) {animation-delay:.15s}.is-playing .voice-waves i:nth-child(3) {animation-delay:.3s}
.voice-bubble:focus-visible {outline:2px solid #08a451;outline-offset:3px}.voice-error {color:#ad3333;background:#fff0f0;padding:5px 8px;border-radius:8px;font-size:12px}
@keyframes wave {to {transform:scaleY(.35)}}@media(prefers-reduced-motion:reduce) {.is-playing .voice-waves i {animation:none}}
</style>
