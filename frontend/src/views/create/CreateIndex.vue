<script setup>
import {onMounted, ref, watch} from 'vue'
import CreateCharacter from '@/views/create/character/CreateCharacter.vue'
import Character from '@/components/character/Character.vue'
import api from '@/js/http/api.js'
import {useUserStore} from '@/stores/user.js'
const tab = ref('characters')
const editor = ref(null)
const characters = ref([])
const error = ref('')
const busy = ref(false)
const hasMore = ref(false)
const user = useUserStore()
async function load(reset=true) {
  if (!user.isLogin() || busy.value) return
  busy.value = true; error.value = ''
  if (reset) characters.value = []
  try {
    const {data} = await api.get('/api/create/character/get_list/', {params:{user_id:user.id, items_count:characters.value.length, archived:tab.value==='archived'}})
    characters.value.push(...data.characters); hasMore.value = data.characters.length===20
  } catch (e) {error.value = e.response?.data?.result || '角色加载失败，请重试'}
  finally {busy.value = false}
}
function choose(value) {if(tab.value==='new' && value!==tab.value && editor.value?.hasUnsavedChanges() && !window.confirm('改动尚未保存，确定离开吗？')) return;tab.value=value; if (value!=='new') load()}
onMounted(() => {if(user.isLogin()) load()})
watch(() => user.id,id => {if(id) load()})
</script>
<template>
  <section class="panel p-5 mb-5">
    <h1 class="text-xl font-bold">创作中心</h1>
    <div class="flex flex-wrap gap-2 mt-3">
      <button class="soft-button" :disabled="busy" @click="choose('characters')">我的角色</button>
      <button class="soft-button" :disabled="busy" @click="choose('new')">新建角色</button>
      <button class="soft-button" :disabled="busy" @click="choose('archived')">已归档</button>
      <RouterLink class="soft-button" :to="{name:'creator-resources'}">知识、音色与任务</RouterLink>
    </div>
  </section>
  <CreateCharacter ref="editor" v-if="tab==='new'" />
  <template v-else>
    <p v-if="error" class="form-error" role="alert">{{error}} <button @click="load()">重试</button></p>
    <div class="character-grid"><Character v-for="character in characters" :key="character.id" :character="character" :canEdit="true" @remove="load()" /></div>
    <p v-if="busy" role="status">加载中…</p>
    <p v-else-if="!characters.length && !error" class="empty-state">{{tab==='archived' ? '暂无归档角色' : '还没有角色，点击新建角色开始创作。'}}</p>
    <button v-if="hasMore" class="soft-button" :disabled="busy" @click="load(false)">加载更多</button>
  </template>
</template>
