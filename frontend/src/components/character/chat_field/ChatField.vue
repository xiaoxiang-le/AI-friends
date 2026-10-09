<script setup>
import {computed, nextTick, ref, useTemplateRef} from "vue";
import InputField from "@/components/character/chat_field/input_field/InputField.vue";
import CharacterPhotoField from "@/components/character/chat_field/character_photo_field/CharacterPhotoField.vue";
import ChatHistory from "@/components/character/chat_field/chat_history/ChatHistory.vue";
import { resolveMediaUrl } from "@/js/http/api.js";

const props = defineProps(['friend'])
const modalRef = useTemplateRef('modal-ref')
const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')
const history = ref([])

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
        :friendId="friend.id"
        @pushBackMessage="handlePushBackMessage"
        @addToLastMessage="handleAddToLastMessage"
      />
      <CharacterPhotoField v-if="friend" :character="friend.character" />
    </div>
  </dialog>
</template>

<style scoped>

</style>