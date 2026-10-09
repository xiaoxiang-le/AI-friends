<script setup>
import KeyboardIcon from "@/components/character/icons/KeyboardIcon.vue";
import {onBeforeUnmount, onMounted, ref} from "vue";
import {MicVAD} from "@ricky0123/vad-web";
import api from "@/js/http/api.js";
import CONFIG_API from "@/js/config/config.js";

const emit = defineEmits(['close', 'send', 'stop'])
const isSpeaking = ref(false)
const errorMessage = ref('')
const transcript = ref('')
const recognizing = ref(false)
let disposed = false
let requestController = null

let vadInstance = null;

const startRecording = async () => {
  const baseUrl = CONFIG_API.VAD_URL
  try {
    vadInstance = await MicVAD.new({
      baseAssetPath: baseUrl,
      onSpeechStart: () => {
        isSpeaking.value = true;
        emit('stop')
      },
      onSpeechEnd: (audio) => {
        if (disposed || recognizing.value || transcript.value) return;
        isSpeaking.value = false;
        const pcm16 = float32ToInt16(audio);
        sendToBackend(pcm16);
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
    if (disposed) {await vadInstance.destroy(); vadInstance = null; return}
    await vadInstance.start();
  } catch (e) {
    errorMessage.value = '无法启用麦克风，请检查权限或切换文字输入';
  }
};
// 将 Float32 转 PCM 16-bit
const float32ToInt16 = (float32Array) => {
  const buffer = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    buffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return buffer.buffer;
};

const sendToBackend = async (arrayBuffer) => {
  if (disposed || recognizing.value) return
  recognizing.value = true
  errorMessage.value = ''
  requestController = new AbortController()
  const blob = new Blob([arrayBuffer], { type: "audio/pcm" })
  const formData = new FormData()
  formData.append("audio", blob, 'voice.pcm')

  try {
    const res = await api.post('/api/friend/message/asr/asr/', formData, {signal: requestController.signal, timeout: 50000})
    if (disposed) return
    const data = res.data
    if (data.result === 'success') {
      transcript.value = data.text
    } else {
      errorMessage.value = data.result || '语音识别失败，请重试'
    }
  } catch (err) {
    if (!disposed) errorMessage.value = err.response?.data?.result || '语音识别失败，请重试'
  } finally {recognizing.value = false}
};

onMounted(() => {
  startRecording()
})

onBeforeUnmount(() => {
  disposed = true
  requestController?.abort()
  if (vadInstance) {
    vadInstance.destroy()
    vadInstance = null
  }
})
</script>

<template>
  <p v-if="errorMessage" class="chat-error" role="alert">{{ errorMessage }}</p>
  <div v-if="transcript" class="bg-white p-3 rounded-lg">
    <label for="voice-transcript">确认识别结果（转入文字输入框后发送）</label>
    <textarea id="voice-transcript" v-model="transcript" class="textarea w-full" maxlength="10000" />
    <button type="button" class="btn btn-sm" :disabled="!transcript.trim()" @click="emit('send', null, transcript)">使用识别文字</button>
    <button type="button" class="btn btn-sm" @click="transcript = ''">重新录音</button>
  </div>
  <div class="chat-input bg-black/30 backdrop-blur-sm rounded-2xl">
    <div v-if="isSpeaking" class="flex items-center justify-center gap-1 h-6 flex-1">
      <div
        v-for="i in 32" :key="i"
        class="w-0.5 bg-blue-400 rounded-full animate-wave"
        :style="{ animationDelay: `${i * 0.1}s` }"
      ></div>
    </div>
    <div v-else class="text-white/50 text-base w-full text-center">
      {{ recognizing ? '正在识别…' : transcript ? '请确认识别文字' : '请开始说话' }}
    </div>
    <button type="button" aria-label="切换文字输入" @click="emit('close')" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer">
      <KeyboardIcon />
    </button>
  </div>
</template>

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
