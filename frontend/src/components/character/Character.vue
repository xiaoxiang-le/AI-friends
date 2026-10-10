<script setup>
import {ref, useTemplateRef, computed} from "vue";
import {useUserStore} from "@/stores/user.js";
import UpdateIcon from "@/components/character/icons/UpdateIcon.vue";
import RemoveIcon from "@/components/character/icons/RemoveIcon.vue";
import api, { resolveMediaUrl } from "@/js/http/api.js";
import {useRouter} from "vue-router";
import ChatField from "@/components/character/chat_field/ChatField.vue";

const props = defineProps(['character', 'canEdit', 'canRemoveFriend', 'friendId', 'available']);
const emit = defineEmits(['remove'])
const user = useUserStore()
const router = useRouter()

async function handleRemoveCharacter() {
  try {
    const res = await api.post('/api/create/character/remove/', {
      character_id: props.character.id,
      version: props.character.version,
    })
    if (res.data.result === 'success') {
      emit('remove', props.character.id)
    }
  } catch (err) {
    actionError.value=err.response?.data?.result || '归档失败，请稍后重试'
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
    actionError.value=err.response?.data?.result || '移除好友失败，请重试'
  }
}

const chatFieldRef = useTemplateRef('chat-field-ref')
const friend = ref(null)
const actionError = ref('')
const reporting = ref(false)
const reportReason = ref('')
async function reportCharacter() {
  actionError.value = ''
  try {await api.post('/api/reports/', {character_id:props.character.id,reason:reportReason.value}); reporting.value=false;actionError.value='举报已提交，可在创作资源页查看处理结果'}
  catch(e) {actionError.value=e.response?.data?.result || '举报失败，请稍后重试'}
}
async function restoreCharacter() {
  try {await api.post('/api/create/character/restore/', {character_id:props.character.id,version:props.character.version});emit('remove',props.character.id)}
  catch(e) {actionError.value=e.response?.data?.result || '恢复失败，请刷新重试'}
}

const backgroundImageUrl = computed(() => resolveMediaUrl(props.character?.background_image))
const characterPhotoUrl = computed(() => resolveMediaUrl(props.character?.photo))
const authorPhotoUrl = computed(() => resolveMediaUrl(props.character?.author?.photo))

async function openChatField() {
  if (!user.isLogin()) {
    await router.push({
      name: 'user-account-login-index', query:{redirect:router.currentRoute.value.fullPath}
    })
  } else {
    if(props.friendId) {
      friend.value={id:props.friendId,character:props.character,available:props.available}
      chatFieldRef.value.showModal()
      return
    }
    try {
      const res = await api.post('/api/friend/get_or_create/', {
        character_id: props.character.id,
      })
      const data = res.data
      if (data.result === 'success') {
        friend.value = data.friend
        chatFieldRef.value.showModal();
      } else actionError.value=data.result || '暂时无法打开聊天'
    } catch (err) {
      actionError.value=err.response?.data?.result || '暂时无法打开聊天，请重试'
    }
  }
}
</script>

<template>
  <article class="character-card">
    <button type="button" class="character-cover" @click="openChatField" :aria-label="'认识 ' + character.name"><img v-if="backgroundImageUrl" :src="backgroundImageUrl" alt="" loading="lazy" /><span class="character-type">AI 角色</span><span class="cover-chat">{{available===false ? '查看历史 ↗' : '开始对话 ↗'}}</span></button>
    <div class="character-body">
      <div class="character-title-row"><button type="button" class="character-avatar" @click="openChatField" :aria-label="'和 ' + character.name + ' 聊天'"><img v-if="characterPhotoUrl" :src="characterPhotoUrl" alt="" loading="lazy" /><span v-else>{{ character.name?.slice(0, 1) }}</span></button><div><button type="button" class="character-name" @click="openChatField">{{ character.name }}</button><span class="character-subtitle">一个等待认识的灵魂</span></div></div>
      <p v-if="canEdit" class="text-xs text-gray-500">{{ {draft:'草稿',reviewing:'待审核',rejected:'审核拒绝',published:'已发布',archived:'已归档'}[character.status] }} · {{ {private:'仅自己',unlisted:'不在发现页展示',public:'公开'}[character.visibility] }}</p>
      <p class="character-description">{{ character.profile || '这个角色的故事，等你来探索。' }}</p>
      <div class="character-bottom"><RouterLink :to="{name: 'user-space-index', params: {user_id: character.author.user_id}}" class="character-author"><img v-if="authorPhotoUrl" :src="authorPhotoUrl" alt="" loading="lazy" /><span>{{ character.author.username }}</span></RouterLink><div class="character-actions"><template v-if="canEdit && character.author.user_id === user.id"><RouterLink v-if="character.status!=='archived'" :to="{name: 'update-character', params: {character_id: character.id}}" class="icon-button" aria-label="编辑角色" title="编辑角色"><UpdateIcon /></RouterLink><button v-if="character.status==='archived'" type="button" @click="restoreCharacter" class="soft-button">恢复草稿</button><button v-else type="button" @click="handleRemoveCharacter" class="icon-button" aria-label="归档角色" title="归档角色（可恢复，保留历史）"><RemoveIcon /></button></template><button v-if="canRemoveFriend" type="button" @click="handleRemoveFriend" class="icon-button" aria-label="移除好友" title="移除好友"><RemoveIcon /></button><button type="button" class="card-chat-button" @click="openChatField">{{available===false ? '历史' : '聊天'}} <span>↗</span></button></div></div>
    </div>
    <p v-if="actionError" class="form-error" role="status">{{actionError}}</p>
    <button v-if="user.isLogin() && character.author.user_id!==user.id" class="text-xs p-2 text-gray-500" @click="reporting=!reporting">举报角色</button>
    <form v-if="reporting" class="p-3" @submit.prevent="reportCharacter"><label :for="'report-'+character.id">举报原因</label><input :id="'report-'+character.id" v-model="reportReason" maxlength="200" required class="input w-full"><button class="soft-button" type="submit">提交举报</button></form>
    <ChatField ref="chat-field-ref" :friend="friend" />
  </article>
</template>
