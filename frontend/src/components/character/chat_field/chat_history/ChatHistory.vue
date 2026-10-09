<script setup>
import Message from "@/components/character/chat_field/chat_history/message/Message.vue";
import {nextTick, onBeforeUnmount, onMounted, useTemplateRef, ref} from "vue";
import api from "@/js/http/api.js";

const props = defineProps(['history', 'friendId', 'character'])
const emit = defineEmits(['pushFrontMessage'])
const scrollRef = useTemplateRef('scroll-ref')
const sentinelRef = useTemplateRef('sentinel-ref')
let isLoading = false
let hasMessages = true
let lastMessageId = 0
const errorMessage = ref('')
let disposed = false

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const sentinelRect = sentinelRef.value.getBoundingClientRect()
  const scrollRect = scrollRef.value.getBoundingClientRect()
  return sentinelRect.top < scrollRect.bottom && sentinelRect.bottom > scrollRect.top
}

async function loadMore() {
  if (isLoading || !hasMessages) return
  isLoading = true
  errorMessage.value = ''

  let newMessages = []
  try {
    const res = await api.get('/api/friend/message/get_history/', {
      params: {
        last_message_id: lastMessageId,
        friend_id: props.friendId,
      }
    })
    const data = res.data
    if (disposed) return
    if (data.result === 'success') {
      newMessages = data.messages
    } else {
      throw new Error(data.result || '历史加载失败')
    }
  } catch (err) {
    errorMessage.value = '历史加载失败，请重试'
  } finally {
    isLoading = false

    if (disposed || errorMessage.value) return
    if (newMessages.length === 0) {
      hasMessages = false
    } else {
      const oldHeight = scrollRef.value.scrollHeight
      const oldTop = scrollRef.value.scrollTop

      for (const m of newMessages) {
        emit('pushFrontMessage', {
          role: 'ai',
          content: m.output,
          id: `ai-${m.id}`,
        })
        emit('pushFrontMessage', {
          role: 'user',
          content: m.user_message,
          id: `user-${m.id}`,
        })
        lastMessageId = m.id
      }

      await nextTick()

      const newHeight = scrollRef.value.scrollHeight
      scrollRef.value.scrollTop = oldTop + newHeight - oldHeight

      if (checkSentinelVisible()) {
        await loadMore()
      }
    }
  }
}

let observer = null
onMounted(async () => {
  await loadMore()
  if (disposed) return

  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadMore()
        }
      })
    },
    {root: scrollRef.value, rootMargin: '2px', threshold: 0}
  )

  observer.observe(sentinelRef.value)
})

onBeforeUnmount(() => {
  disposed = true
  observer?.disconnect()
})

async function scrollToBottom() {
  await nextTick()

  scrollRef.value.scrollTop = scrollRef.value.scrollHeight
}

defineExpose({
  scrollToBottom
})
</script>

<template>
  <div ref="scroll-ref" class="chat-history no-scrollbar">
    <div ref="sentinel-ref" class="h-2"></div>
    <button v-if="errorMessage" type="button" class="btn btn-sm" @click="loadMore">{{ errorMessage }}</button>
    <Message
        v-for="message in history"
        :key="message.id"
        :message="message"
        :character="character"
    />
  </div>
</template>

<style scoped>
/* 隐藏 Chrome, Safari 和 Opera 的滚动条 */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}

/* 隐藏 IE, Edge 和 Firefox 的滚动条 */
.no-scrollbar {
  -ms-overflow-style: none; /* IE and Edge */
  scrollbar-width: none; /* Firefox */
}
</style>
