<script setup>
import { useUserStore } from "@/stores/user.js";
import { resolveMediaUrl } from "@/js/http/api.js";

const props = defineProps(['message', 'character'])
const user = useUserStore()
</script>

<template>
  <div v-if="message.content || message.state">
    <div v-if="message.role === 'ai'" class="chat chat-start">
      <div class="chat-image avatar">
        <div class="w-10 rounded-full">
          <img :src="resolveMediaUrl(character?.photo)" alt="">
        </div>
      </div>
      <div class="chat-bubble whitespace-pre-wrap break-all">{{ message.content || (message.state === 'streaming' ? '正在生成…' : '') }}
        <p v-if="message.state === 'failed'" class="text-xs">回复失败，内容尚未保存</p>
        <p v-if="message.state === 'cancelled'" class="text-xs">已停止，部分回复未保存</p>
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

</style>
