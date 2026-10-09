<script setup>
import {ref, useTemplateRef, computed} from "vue";
import {useUserStore} from "@/stores/user.js";
import UpdateIcon from "@/components/character/icons/UpdateIcon.vue";
import RemoveIcon from "@/components/character/icons/RemoveIcon.vue";
import api, { resolveMediaUrl } from "@/js/http/api.js";
import {useRouter} from "vue-router";
import ChatField from "@/components/character/chat_field/ChatField.vue";

const props = defineProps(['character', 'canEdit', 'canRemoveFriend', 'friendId']);
const emit = defineEmits(['remove'])
const user = useUserStore()
const router = useRouter()

async function handleRemoveCharacter() {
  try {
    const res = await api.post('/api/create/character/remove/', {
      character_id: props.character.id,
    })
    if (res.data.result === 'success') {
      emit('remove', props.character.id)
    }
  } catch (err) {
  }
}

async function handleRemoveFriend() {
  try {
    const res = await api.post('/api/friend/remove/', {
      friend_id: props.friendId,
    })
    if (res.data.result === 'success') {
      emit('remove', props.friendId)
    }
  } catch (err) {
    console.error(err)
  }
}

const chatFieldRef = useTemplateRef('chat-field-ref')
const friend = ref(null)

const backgroundImageUrl = computed(() => resolveMediaUrl(props.character?.background_image))
const characterPhotoUrl = computed(() => resolveMediaUrl(props.character?.photo))
const authorPhotoUrl = computed(() => resolveMediaUrl(props.character?.author?.photo))

async function openChatField() {
  if (!user.isLogin()) {
    await router.push({
      name: 'user-account-login-index'
    })
  } else {
    try {
      const res = await api.post('/api/friend/get_or_create/', {
        character_id: props.character.id,
      })
      const data = res.data
      if (data.result === 'success') {
        friend.value = data.friend
        chatFieldRef.value.showModal();
      }
    } catch (err) {
      console.error(err)
    }
  }
}
</script>

<template>
  <article class="character-card">
    <button type="button" class="character-cover" @click="openChatField" :aria-label="'认识 ' + character.name"><img v-if="backgroundImageUrl" :src="backgroundImageUrl" alt="" loading="lazy" /><span class="character-type">AI 角色</span><span class="cover-chat">开始对话 ↗</span></button>
    <div class="character-body">
      <div class="character-title-row"><button type="button" class="character-avatar" @click="openChatField" :aria-label="'和 ' + character.name + ' 聊天'"><img v-if="characterPhotoUrl" :src="characterPhotoUrl" alt="" loading="lazy" /><span v-else>{{ character.name?.slice(0, 1) }}</span></button><div><button type="button" class="character-name" @click="openChatField">{{ character.name }}</button><span class="character-subtitle">一个等待认识的灵魂</span></div></div>
      <p class="character-description">{{ character.profile || '这个角色的故事，等你来探索。' }}</p>
      <div class="character-bottom"><RouterLink :to="{name: 'user-space-index', params: {user_id: character.author.user_id}}" class="character-author"><img v-if="authorPhotoUrl" :src="authorPhotoUrl" alt="" loading="lazy" /><span>{{ character.author.username }}</span></RouterLink><div class="character-actions"><template v-if="canEdit && character.author.user_id === user.id"><RouterLink :to="{name: 'update-character', params: {character_id: character.id}}" class="icon-button" aria-label="编辑角色" title="编辑角色"><UpdateIcon /></RouterLink><button type="button" @click="handleRemoveCharacter" class="icon-button" aria-label="删除角色" title="删除角色"><RemoveIcon /></button></template><button v-if="canRemoveFriend" type="button" @click="handleRemoveFriend" class="icon-button" aria-label="移除好友" title="移除好友"><RemoveIcon /></button><button type="button" class="card-chat-button" @click="openChatField">聊天 <span>↗</span></button></div></div>
    </div>
    <ChatField ref="chat-field-ref" :friend="friend" />
  </article>
</template>
