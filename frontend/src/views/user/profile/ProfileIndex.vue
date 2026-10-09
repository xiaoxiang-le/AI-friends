<script setup>

import Photo from "@/views/user/profile/components/Photo.vue";
import Username from "@/views/user/profile/components/Username.vue";
import Profile from "@/views/user/profile/components/Profile.vue";
import {useUserStore} from "@/stores/user.js";
import {ref, useTemplateRef} from "vue";
import {base64ToFile} from "@/js/utils/base64_to_file.js";
import api from "@/js/http/api.js";

const user = useUserStore()

const photoRef = useTemplateRef('photo-ref')
const usernameRef = useTemplateRef('username-ref')
const profileRef = useTemplateRef('profile-ref')
const errorMessage = ref('')
const submitting = ref(false)
const successMessage = ref('')

async function handleUpdate() {
  if (submitting.value) return
  successMessage.value = ''
  const photo = photoRef.value.myPhoto;
  const username = (usernameRef.value.myUsername || '').trim();
  const profile = (profileRef.value.myProfile || '').trim();

  errorMessage.value = '';
  if (!photo) {
    errorMessage.value = '头像不能为空';
  } else if (!username) {
    errorMessage.value = '用户名不能为空';
  } else if (!profile) {
    errorMessage.value = '简介不能为空';
  } else {
    submitting.value = true
    const formData = new FormData();
    formData.append("username", username);
    formData.append("profile", profile);
    if (photo !== user.photo && typeof photo === "string" && photo.startsWith("data:")) {
      const file = base64ToFile(photo, "photo.png");
      if (file) formData.append("photo", file);
    }

    try {
      const res = await api.post('/api/user/profile/update/', formData);
      const data = res.data;
      if (data.result === 'success') {
        user.setUserInfo(data);
        successMessage.value = '资料已更新';
      } else {
        errorMessage.value = data.result;
      }
    } catch(err) {
      errorMessage.value = '暂时无法连接，请稍后重试';
    } finally {
      submitting.value = false;
    }
  }
}
</script>

<template>
  <div class="flex justify-center">
    <div class="card editor-card">
      <div class="card-body">
        <h3 class="text-lg font-bold my-4">编辑资料</h3>
        <Photo ref="photo-ref" :photo="user.photo"/>
        <Username ref="username-ref" :username="user.username"/>
        <Profile ref="profile-ref" :profile="user.profile"/>

        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

        <p v-if="successMessage" class="text-green-700" role="status">{{ successMessage }}</p>
        <div class="flex justify-center">
          <button @click="handleUpdate" class="btn btn-neutral editor-submit" :disabled="submitting">更新</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>