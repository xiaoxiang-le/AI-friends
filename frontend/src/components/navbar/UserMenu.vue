<script setup>
import { computed } from "vue";
import { useUserStore } from "@/stores/user.js";
import { useRouter } from "vue-router";
import api from "@/js/http/api.js";
import { BASE_URL } from "@/js/http/api.js";
import UserSpaceIcon from "@/components/navbar/icons/UserSpaceIcon.vue";
import UserProfileIcon from "@/components/navbar/icons/UserProfileIcon.vue";
import UserLogoutIcon from "@/components/navbar/icons/UserLogoutIcon.vue";

const user = useUserStore();
const router = useRouter();

// 开发环境下后端返回 /media/... 相对路径，需拼上后端地址才能正确加载头像
const photoUrl = computed(() => {
  const p = user.photo;
  if (!p) return "";
  if (p.startsWith("http")) return p;
  return BASE_URL ? BASE_URL + p : p;
});

function closeMenu() {
  const element = document.activeElement;
  if (element && element instanceof HTMLElement) element.blur();
}

async function handleLogout() {
  try {
    await api.post("/api/user/account/logout/", {});
  } catch (e) {
    console.log(e);
  } finally {
    user.logout();
    closeMenu();
    router.push({ name: "homepage-index" });
  }
}
</script>

<template>
<div class="dropdown dropdown-end">
  <div tabindex="0" role="button" aria-label="打开账户菜单" class="avatar btn btn-circle w-8 h-8 mr-6">
    <div class="w-8 rounded-full">
      <img :src="photoUrl" alt="">
    </div>
  </div>
  <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-1 w-48 p-2 shadow-sm">
    <li>
      <RouterLink @click="closeMenu" :to="{ name: 'user-space-index', params: { user_id: user.id } }">
        <div class="avatar">
          <div class="w-10 rounded-full">
            <img :src="photoUrl" alt="">
          </div>
        </div>
        <span class="text-base font-bold line-clamp-1 break-all">{{ user.username }}</span>
      </RouterLink>
    </li>
    <li>
      <RouterLink @click="closeMenu" :to="{ name: 'user-space-index', params: { user_id: user.id } }" class="text-sm font-bold py-3">
        <UserSpaceIcon />
        个人空间
      </RouterLink>
    </li>
    <li>
      <RouterLink @click="closeMenu" :to="{ name: 'user-profile-index' }" class="text-sm font-bold py-3">
        <UserProfileIcon />
        编辑资料
      </RouterLink>
    </li>
    <li>
      <button type="button" class="text-sm font-bold py-3 w-full text-left" @click="handleLogout">
        <UserLogoutIcon />
        退出
      </button>
    </li>
  </ul>
</div>
</template>

<style scoped>

</style>
