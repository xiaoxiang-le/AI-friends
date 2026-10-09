<script setup>

import {nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch} from "vue";
import api from "@/js/http/api.js";
import Character from "@/components/character/Character.vue";
import { useUserStore } from "@/stores/user.js";

const user = useUserStore();
const friends = ref([]);
const isLoading = ref(false);
const hasFriends = ref(true);
const sentinelRef = useTemplateRef('sentinel-ref');
const loadError = ref('');
watch(() => user.hasPulledUserInfo, ready => {
  if (ready && user.isLogin()) loadMore();
});


function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

async function loadMore() {
  if (!user.isLogin() || isLoading.value || !hasFriends.value) return;
  isLoading.value = true;
  loadError.value = '';

  let newFriends = [];

  try {
    const res = await api.get('/api/friend/get_list/', {
      params: {
        items_count: friends.value.length,
      }
    });
    const data = res.data;
    if (data.result === 'success') {
      newFriends = data.friends ?? [];
    } else {
      loadError.value = data.result || '好友加载失败，请重试';
    }

  }catch(err) {
    loadError.value = '好友加载失败，请重试';
  }finally {
    isLoading.value = false;
    if (loadError.value) return;
    if (newFriends.length === 0) {
      hasFriends.value = false
    } else {
      friends.value.push(...newFriends);
      await nextTick();

      if (checkSentinelVisible()) {
        await loadMore();
      }
    }
  }
}

let observer = null;

onMounted(async () => {
  await loadMore()  // 加载新元素

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

  //监听哨兵元素， 每次哨兵被看到时，都会触发一次
  observer.observe(sentinelRef.value)
})

function removeFriend (friendId) {
  friends.value = friends.value.filter(f => f.id !== friendId)
}

onBeforeUnmount(() => {
  observer?.disconnect()  // 解绑监听器
})

</script>

<template>
  <div>
    <div class="feed-heading"><div><span class="eyebrow">保持连接</span><h2>我的好友</h2><p>熟悉的声音，和还没聊完的故事。</p></div><RouterLink :to="{ name: 'homepage-index' }" class="soft-button">发现新朋友 ↗</RouterLink></div>
    <div class="character-grid">
      <Character
        v-for="friend in friends"
        :key="friend.id"
        :character="friend.character"
        :canRemoveFriend="true"
        :friendId="friend.id"
        @remove="removeFriend"
      />
    </div>

    <div v-if="loadError" class="form-error" role="alert">{{ loadError }} <button class="soft-button" @click="loadMore">重新加载</button></div>
    <div v-else-if="!isLoading && !friends.length && !hasFriends" class="empty-state"><span class="empty-icon">♡</span><h3>这里将留下你的相遇</h3><p>去发现一个喜欢的角色，聊一句你好，就能在这里继续对话。</p><RouterLink :to="{ name: 'homepage-index' }" class="soft-button">发现新朋友 →</RouterLink></div>
    <div ref="sentinel-ref" class="feed-sentinel"></div>
    <div v-if="isLoading" class="text-gray-500 mt-4">加载中……</div>
    <div v-else-if="!hasFriends && friends.length" class="feed-status">你的好友都在这里了</div>
  </div>
</template>

<style scoped>
</style>
