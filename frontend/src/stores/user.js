import { defineStore } from "pinia";
import { ref } from "vue";

export const useUserStore = defineStore('user', () => {
    const id = ref(0);
    const username = ref("");
    const photo = ref("");
    const profile = ref("");
    const accessToken = ref("");
    const hasPulledUserInfo = ref(false);

    function isLogin() {
        return !!accessToken.value
    }

    function setAccessToken(token) {
        accessToken.value = token;
    }

    function setUserInfo(data) {
        id.value = data.user_id;
        username.value = data.username;
        photo.value = data.photo;
        profile.value = data.profile;
    }

    function logout() {
        id.value = 0;
        username.value = "";
        photo.value = "";
        profile.value = "";
        accessToken.value = "";
        // 仍然保留 “已经拉取过用户信息” 的标记，
        // 这样导航栏可以立刻根据未登录状态展示“登录”按钮
        hasPulledUserInfo.value = true;
    }

    function setHasPulledUserInfo(newStatus) {
        hasPulledUserInfo.value = newStatus;
    }

    return {
        id,
        username,
        photo,
        profile,
        accessToken,
        hasPulledUserInfo,
        isLogin,
        setAccessToken,
        setUserInfo,
        logout,
        setHasPulledUserInfo,
    }
})
