<script setup>
import {computed, nextTick, ref, useTemplateRef, watch} from "vue";
import api from '@/js/http/api.js';
import InputField from "@/components/character/chat_field/input_field/InputField.vue";
import CharacterPhotoField from "@/components/character/chat_field/character_photo_field/CharacterPhotoField.vue";
import ChatHistory from "@/components/character/chat_field/chat_history/ChatHistory.vue";
import { resolveMediaUrl } from "@/js/http/api.js";

const props = defineProps(['friend'])
const modalRef = useTemplateRef('modal-ref')
const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')
const history = ref([])
const showMemory = ref(false)
const memory = ref('')
const memoryVersion = ref(0)
const memoryMessage = ref('')
const memoryBusy = ref(false)
const memoryLoaded = ref(false)
watch(() => props.friend?.id, () => {history.value = []; showMemory.value = false})
async function loadMemory() {
  showMemory.value = true
  memoryMessage.value = ''
  memoryBusy.value = true
  memoryLoaded.value = false
  try {
    const {data} = await api.get('/api/friend/memory/', {params: {friend_id: props.friend.id}})
    memory.value = data.memory
    memoryVersion.value = data.version
    memoryLoaded.value = true
  } catch (err) {
    memoryMessage.value = err.response?.data?.result || '记忆加载失败'
  } finally {memoryBusy.value = false}
}
async function saveMemory() {
  memoryBusy.value = true
  try {
    const {data} = await api.post('/api/friend/memory/', {friend_id: props.friend.id, memory: memory.value, version: memoryVersion.value})
    memoryVersion.value = data.version
    memoryMessage.value = '记忆已保存'
  } catch (err) {
    memoryMessage.value = err.response?.data?.result || '记忆保存失败'
  } finally {memoryBusy.value = false}
}
function setMessageAudio(url) {
  const last = history.value.at(-1)
  if (last?.role === 'ai') last.audioUrl = url
  chatHistoryRef.value?.scrollToBottom()
}
function setMessageState(state) {
  const last = history.value.at(-1)
  if (last?.role === 'ai') last.state = state
}

async function showModal() {
  modalRef.value.showModal()

  await nextTick()
  inputRef.value.focus()
}

function handleClose() {
  inputRef.value?.close()
}

const modalStyle = computed(() => {
  if (props.friend?.character?.background_image) {
    return {
      backgroundImage: `url(${resolveMediaUrl(props.friend.character.background_image)})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
  }
  return {}
})

function handlePushBackMessage(msg) {
  history.value.push(msg)
  chatHistoryRef.value.scrollToBottom()
}

function handleAddToLastMessage(delta) {
  const last = history.value.at(-1)
  if (last?.role === 'ai') last.content += delta
  chatHistoryRef.value.scrollToBottom()
}

function handlePushFrontMessage(msg) {
  history.value.unshift(msg)
}

defineExpose({
  showModal,
})
</script>

<template>
  <dialog ref="modal-ref" class="modal" @close="handleClose">
    <div class="modal-box chat-modal" :style="modalStyle">
      <button type="button" class="btn btn-sm self-start" @click="loadMemory">长期记忆</button>
      <div v-if="showMemory" class="bg-white p-3 rounded-lg">
        <label for="chat-memory">此会话的长期记忆（最多5000字）</label>
        <textarea id="chat-memory" v-model="memory" maxlength="5000" :disabled="memoryBusy" class="textarea w-full" />
        <p role="status">{{ memoryMessage }}</p>
        <button type="button" class="btn btn-sm" :disabled="memoryBusy || !memoryLoaded" @click="saveMemory">保存记忆</button>
        <button type="button" class="btn btn-sm" :disabled="memoryBusy || !memoryLoaded" @click="memory = ''">清空内容</button>
        <button type="button" class="btn btn-sm" :disabled="memoryBusy" @click="loadMemory">重新加载</button>
        <button type="button" class="btn btn-sm" @click="showMemory = false">收起</button>
      </div>
      <button aria-label="关闭聊天" type="button" @click="modalRef.close()" class="btn btn-sm btn-circle btn-ghost bg-transparent absolute right-1 top-1">✕</button>
      <ChatHistory
        ref="chat-history-ref"
        v-if="friend"
        :key="friend.id"
        :history="history"
        :friendId="friend.id"
        :character="friend.character"
        @pushFrontMessage="handlePushFrontMessage"
      />
      <InputField
        v-if="friend"
        ref="input-ref"
        :key="friend.id"
        :friendId="friend.id"
        @pushBackMessage="handlePushBackMessage"
        @addToLastMessage="handleAddToLastMessage"
        @setMessageState="setMessageState"
        @setMessageAudio="setMessageAudio"
      />
      <CharacterPhotoField v-if="friend" :character="friend.character" />
    </div>
  </dialog>
</template>

<style scoped>

</style>
