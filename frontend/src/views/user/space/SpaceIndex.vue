<script setup>
import UserInfoField from "@/views/user/space/components/UserInfoField.vue";
import {nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch} from "vue";
import {useRoute} from "vue-router";
import api from "@/js/http/api.js";
import Character from "@/components/character/Character.vue";

import {useUserStore} from '@/stores/user.js'
const user=useUserStore()
watch(() => user.id, () => reset())
const userProfile = ref(null)
const characters = ref([])
const isLoading = ref(false)
const hasCharacters = ref(true)
const sentinelRef = useTemplateRef('sentinel-ref')
const route = useRoute()
const loadError = ref('')
let generation = 0

function reset() {
  generation++
  userProfile.value = null;
  characters.value = [];
  isLoading.value = false;
  hasCharacters.value = true;
  loadMore()
}

watch(() => route.params.user_id, () => {
  reset();
})

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

async function loadMore() {
  if (isLoading.value || !hasCharacters.value) return
  isLoading.value = true
  const requestGeneration = generation
  loadError.value = ''

  let newCharacters = []
  try {
    const res = await api.get('/api/create/character/get_list/', {
      params: {
        items_count: characters.value.length,
        user_id: route.params.user_id,
      }
    })
    const data = res.data
    if (requestGeneration !== generation) return
    if (data.result === 'success') {
      userProfile.value = data.user_profile
      newCharacters = data.characters
    } else {
      loadError.value = data.result || '个人空间加载失败'
    }
  } catch (err) {
    if (requestGeneration === generation) loadError.value = '个人空间加载失败，请重试'
  } finally {
    if (requestGeneration !== generation) return
    isLoading.value = false
    if (loadError.value) return
    if (newCharacters.length === 0) {
      hasCharacters.value = false
    } else {
      characters.value.push(...newCharacters)
      await nextTick()

      if (checkSentinelVisible()) {
        await loadMore()
      }
    }
  }
}

let observer = null
onMounted(async () => {
  await loadMore()

  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadMore()
        }
      })
    },
    {root: null, rootMargin: '2px', threshold: 0}
  )
  observer.observe(sentinelRef.value)
})

function removeCharacter(characterId) {
  characters.value = characters.value.filter(c => c.id !== characterId)
}

onBeforeUnmount(() => {
  generation++
  observer?.disconnect()
})
</script>

<template>
  <div>
    <UserInfoField :userProfile="userProfile" />
    <div class="feed-heading"><div><h2>创作的角色</h2><p>把想象变成一个个有个性的朋友。</p></div><span class="feed-badge">角色空间</span></div>
    <div class="character-grid">
      <Character
        v-for="character in characters"
        :key="character.id"
        :character="character"
        :canEdit="true"
        @remove="removeCharacter"
      />
    </div>
    <div v-if="loadError" class="form-error" role="alert">{{ loadError }} <button class="soft-button" @click="loadMore">重新加载</button></div>
    <div v-else-if="!isLoading && !characters.length && !hasCharacters" class="empty-state"><span class="empty-icon">✦</span><h3>故事还在酝酿中</h3><p>这个空间暂时还没有发布角色。</p></div>
    <div ref="sentinel-ref" class="feed-sentinel"></div>
    <div v-if="isLoading" class="text-gray-500 mt-4">加载中...</div>
    <div v-else-if="!hasCharacters && characters.length" class="feed-status">全部角色都在这里了</div>
  </div>
</template>

<style scoped>

</style>
