<script setup>
import {ref, watch, nextTick, onBeforeUnmount, useTemplateRef} from "vue";
import { useUserStore } from "@/stores/user.js";
import { resolveMediaUrl } from "@/js/http/api.js";

const props = defineProps(['message', 'character'])
const user = useUserStore()
const player = useTemplateRef('voice-player')
const playing = ref(false)
const duration = ref(0)
const voiceError = ref('')
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
onBeforeUnmount(() => player.value?.pause())
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
      <div class="chat-bubble whitespace-pre-wrap break-all">{{ message.content || (message.state === 'streaming' ? '正在生成…' : '') }}
        <p v-if="message.state === 'failed'" class="text-xs">回复失败，内容尚未保存</p>
        <p v-if="message.state === 'cancelled'" class="text-xs">已停止，部分回复未保存</p>
      </div>
      <button v-if="message.audioUrl" type="button" class="voice-bubble" :class="{'is-playing':playing}"
        :aria-label="playing ? '暂停角色语音' : '播放角色语音'" :aria-pressed="playing" @click="playVoice">
        <span class="voice-waves" aria-hidden="true"><i /><i /><i /></span>
        <span>{{ duration ? `${duration}″` : '语音回复' }}</span>
        <span class="voice-caption">{{ playing ? '播放中' : '点击播放' }}</span>
      </button>
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
.voice-bubble {display:flex;align-items:center;gap:13px;min-width:152px;padding:12px 15px;border:1px solid #d8e8dc;border-radius:4px 16px 16px 16px;background:#f6fff8;color:#254832;font-size:15px;cursor:pointer;box-shadow:0 1px 3px #0000000a}
.voice-caption {font-size:11px;color:#8b9c90;margin-left:8px}.voice-bubble.is-playing {background:#dcf9e5;border-color:#9ce2b6}
.voice-waves {display:flex;align-items:center;gap:3px;height:22px}.voice-waves i {width:3px;border-radius:3px;background:#08a451;height:7px}.voice-waves i:nth-child(2) {height:13px}.voice-waves i:nth-child(3) {height:19px}
.is-playing .voice-waves i {animation:wave .8s ease-in-out infinite alternate}.is-playing .voice-waves i:nth-child(2) {animation-delay:.15s}.is-playing .voice-waves i:nth-child(3) {animation-delay:.3s}
.voice-bubble:focus-visible {outline:2px solid #08a451;outline-offset:3px}.voice-error {color:#ad3333;background:#fff0f0;padding:5px 8px;border-radius:8px;font-size:12px}
@keyframes wave {to {transform:scaleY(.35)}}@media(prefers-reduced-motion:reduce) {.is-playing .voice-waves i {animation:none}}
</style>
