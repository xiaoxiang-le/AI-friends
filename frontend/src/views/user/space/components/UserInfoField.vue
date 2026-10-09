<script setup>
import { resolveMediaUrl } from '@/js/http/api.js'
import { useUserStore } from '@/stores/user.js'
defineProps(['userProfile'])
const user = useUserStore()
</script>
<template>
  <section v-if="userProfile" class="profile-header panel">
    <div class="profile-cover"><span>每个灵魂，都有自己的故事。 ✦</span></div>
    <div class="profile-content"><div class="profile-avatar"><img :src="resolveMediaUrl(userProfile.photo)" :alt="userProfile.username" /></div><div class="profile-copy"><h1>{{ userProfile.username }}</h1><span class="field-hint">AIFriends · @{{ userProfile.user_id }}</span><p>{{ userProfile.profile || '欢迎来到我的空间，一起探索新的故事。' }}</p></div><RouterLink v-if="userProfile.user_id === user.id" :to="{ name: 'user-profile-index' }" class="soft-button">编辑资料</RouterLink></div>
  </section>
</template>
