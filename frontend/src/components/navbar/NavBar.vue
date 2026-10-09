<script setup>
import HomepageIcon from '@/components/navbar/icons/HomepageIcon.vue'
import FriendIcon from '@/components/navbar/icons/FriendIcon.vue'
import CreateIcon from '@/components/navbar/icons/CreateIcon.vue'
import SearchIcon from '@/components/navbar/icons/SearchIcon.vue'
import UserMenu from '@/components/navbar/UserMenu.vue'
import { useUserStore } from '@/stores/user.js'
import { useRoute, useRouter } from 'vue-router'
import { computed, ref, watch } from 'vue'
const user = useUserStore()
const router = useRouter()
const route = useRoute()
const searchQuery = ref('')
const isAuth = computed(() => ['user-account-login-index', 'user-account-register-index'].includes(route.name))
const links = [
  { name: 'homepage-index', label: '发现', icon: HomepageIcon },
  { name: 'friend-index', label: '我的好友', icon: FriendIcon },
  { name: 'create-index', label: '创作中心', icon: CreateIcon },
]
watch(() => route.query.q, q => { searchQuery.value = q || '' }, { immediate: true })
function handleSearch() {
  router.push({ name: 'homepage-index', query: searchQuery.value.trim() ? { q: searchQuery.value.trim() } : {} })
}
</script>
<template>
  <div v-if="isAuth" class="auth-shell"><slot /></div>
  <div v-else class="social-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <header class="topbar">
      <RouterLink :to="{ name: 'homepage-index' }" class="brand" aria-label="AIFriends 首页"><span class="brand-symbol">af<span></span></span><span>AIFriends</span></RouterLink>
      <form @submit.prevent="handleSearch" class="global-search" role="search"><SearchIcon /><input v-model="searchQuery" aria-label="搜索角色" placeholder="搜索角色、名字或故事" type="search" /></form>
      <nav class="top-links" aria-label="快捷导航"><RouterLink v-for="link in links" :key="link.name" :to="{ name: link.name }" :aria-label="link.label" :title="link.label" active-class="selected"><component :is="link.icon" /></RouterLink></nav>
      <div class="topbar-account">
        <template v-if="user.isLogin()"><RouterLink :to="{ name: 'create-index' }" class="soft-button compact">＋ 创作</RouterLink><UserMenu /></template>
        <template v-else><RouterLink :to="{ name: 'user-account-login-index' }" class="text-button">登录</RouterLink><RouterLink :to="{ name: 'user-account-register-index' }" class="primary-button compact">注册</RouterLink></template>
      </div>
    </header>
    <div class="social-layout">
      <aside class="left-rail">
        <div class="rail-label">你的社交空间</div>
        <nav class="side-links" aria-label="主导航">
          <RouterLink v-for="link in links" :key="link.name" :to="{ name: link.name }" active-class="selected"><component :is="link.icon" /><span>{{ link.label }}</span><span class="nav-arrow">›</span></RouterLink>
          <RouterLink v-if="user.isLogin()" :to="{ name: 'user-space-index', params: { user_id: user.id } }" active-class="selected"><span class="initial-avatar">{{ user.username?.slice(0, 1) }}</span><span>个人主页</span><span class="nav-arrow">›</span></RouterLink>
        </nav>
        <div class="rail-invite"><span class="rail-invite-icon">✦</span><h3>让想象成为朋友</h3><p>赋予角色个性、声音和故事，开启属于你的对话。</p><RouterLink :to="{ name: 'create-index' }">创建一个角色 <span>↗</span></RouterLink></div>
        <footer class="rail-footer">AIFriends · AI 角色社区<br /><span>连接灵感，也连接彼此。</span></footer>
      </aside>
      <main id="main-content" class="main-content" tabindex="-1"><slot /></main>
    </div>
    <nav class="mobile-nav" aria-label="移动端导航"><RouterLink v-for="link in links" :key="link.name" :to="{ name: link.name }" active-class="selected"><component :is="link.icon" /><span>{{ link.label }}</span></RouterLink></nav>
  </div>
</template>
