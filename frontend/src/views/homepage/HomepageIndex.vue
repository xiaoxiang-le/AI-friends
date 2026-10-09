<script setup>
import {nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch} from "vue";
import api from "@/js/http/api.js";
import Character from "@/components/character/Character.vue";
import {useRoute} from "vue-router";

const characters = ref([])
const isLoading = ref(false)
const hasCharacters = ref(true)
const sentinelRef = useTemplateRef('sentinel-ref')
const route = useRoute()
const loadError = ref('')
let requestGeneration = 0

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

async function loadMore() {
  if (isLoading.value || !hasCharacters.value) return
  isLoading.value = true
  const generation = requestGeneration

  loadError.value = ''
  let newCharacters = []
  try {
    const res = await api.get('/api/homepage/index/', {
      params: {
        items_count: characters.value.length,
        search_query: route.query.q || '',
      }
    })
    const data = res.data
    if (generation !== requestGeneration) return
    if (data.result === 'success') {
      newCharacters = data.characters ?? []
    } else {
      loadError.value = '角色暂时加载失败，请稍后重试。'
    }
  } catch (err) {
    if (generation === requestGeneration) loadError.value = '角色暂时加载失败，请稍后重试。'
  } finally {
    if (generation !== requestGeneration) return
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
  if (sentinelRef.value) observer.observe(sentinelRef.value)
})

function reset() {
  requestGeneration++
  characters.value = []
  isLoading.value = false
  hasCharacters.value = true
  loadMore()
}

watch(() => route.query.q, newQ => {
  reset()
})

onBeforeUnmount(() => {
  requestGeneration++
  observer?.disconnect()
})
</script>

<template>
  <div class="discover-layout">
    <div class="discover-feed">
      <section class="welcome-card"><div><span class="eyebrow">你的 AI 社交世界</span><h1>每次相遇，都有新故事<span>✦</span></h1><p>发现有趣的角色，找到与你同频的陪伴。</p><RouterLink :to="{ name: 'create-index' }" class="primary-button">创造你的 AI 好友 <span>↗</span></RouterLink></div><div class="welcome-art" aria-hidden="true"><span>☺</span><span>✦</span><span>☀</span></div></section>
      <div class="feed-heading"><div><h2>{{ route.query.q ? '搜索结果' : '发现新朋友' }}</h2><p>{{ route.query.q ? '关于「' + route.query.q + '」的角色' : '一个角色，一个等待被认识的世界。' }}</p></div><span class="feed-badge">{{ route.query.q ? '角色搜索' : '社区角色' }}</span></div>
      <div class="character-grid"><Character v-for="character in characters" :key="character.id" :character="character" /></div>
      <div v-if="loadError" class="empty-state" role="alert"><span class="empty-icon">!</span><h3>连接暂时中断</h3><p>{{ loadError }}</p><button class="soft-button" @click="hasCharacters = true; loadMore()">重新加载</button></div>
      <div v-else-if="!isLoading && !characters.length && !hasCharacters" class="empty-state"><span class="empty-icon">✦</span><h3>{{ route.query.q ? '还没有找到这个角色' : '第一个故事，等你开启' }}</h3><p>{{ route.query.q ? '试试其他名字或关键词，也许会有新的相遇。' : '社区还没有角色。带着你的想象，创建第一个 AI 好友吧。' }}</p><RouterLink :to="{ name: route.query.q ? 'homepage-index' : 'create-index' }" class="soft-button">{{ route.query.q ? '发现全部角色' : '创建角色' }} <span>→</span></RouterLink></div>
      <div ref="sentinel-ref" class="feed-sentinel"></div>
      <p v-if="isLoading" class="feed-status" role="status"><span class="loading loading-spinner loading-sm"></span> 正在寻找新朋友…</p>
      <p v-else-if="!hasCharacters && characters.length" class="feed-status">你已经看完了所有角色，新的故事等待你的创作。</p>
    </div>
    <aside class="right-rail">
      <section class="panel community-guide"><span class="eyebrow">从这里开始</span><h3>认识 AIFriends</h3><div class="guide-row"><span>01</span><div><h4>发现一个角色</h4><p>从名字和故事里，找到共同话题。</p></div></div><div class="guide-row"><span>02</span><div><h4>说一句你好</h4><p>用文字或语音，开始新的对话。</p></div></div><div class="guide-row"><span>03</span><div><h4>创造你的世界</h4><p>设计角色，分享你的奇思妙想。</p></div></div><RouterLink :to="{ name: 'friend-index' }" class="soft-button">去我的好友 <span>→</span></RouterLink></section>
      <section class="community-note"><span>✧</span><h3>每一种个性，都值得被看见。</h3><p>这里的朋友由 AI 驱动，故事由你创造。</p></section>
      <p class="right-footer">AIFriends · 让灵感有回应</p>
    </aside>
  </div>
</template>
