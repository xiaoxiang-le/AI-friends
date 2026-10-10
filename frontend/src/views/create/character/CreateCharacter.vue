<script setup>
import Photo from "@/views/create/character/components/Photo.vue";
import Name from "@/views/create/character/components/Name.vue";
import Profile from "@/views/create/character/components/Profile.vue";
import BackgroundImage from "@/views/create/character/components/BackgroundImage.vue";
import {onMounted, ref, useTemplateRef} from "vue";
import {base64ToFile} from "@/js/utils/base64_to_file.js";
import api from "@/js/http/api.js";
import {useRouter} from "vue-router";
import {useUserStore} from "@/stores/user.js";
import Voice from "@/views/create/character/components/Voice.vue";

import PublishSettings from '@/views/create/character/components/PublishSettings.vue'
const publishRef = useTemplateRef('publish-ref')
const user = useUserStore()
const router = useRouter()

const photoRef = useTemplateRef('photo-ref')
const nameRef = useTemplateRef('name-ref')
const voiceRef = useTemplateRef('voice-ref')
const profileRef = useTemplateRef('profile-ref')
const backgroundImageRef = useTemplateRef('background-image-ref')
const errorMessage = ref('')
const submitting = ref(false)
const successMessage = ref('')
let saved = false

const voices = ref([])
const curVoiceId = ref(null)

onMounted(async () => {
  try {
    const res = await api.get('/api/create/character/voice/get_list/', {})
    const data = res.data
    if (data.result === 'success') {
      voices.value = data.voices
      curVoiceId.value = data.voices[0]?.id ?? null
      if (!data.voices.length) errorMessage.value = '暂无可用音色，请联系管理员添加音色'
    }
  } catch (err) {
    errorMessage.value = '音色加载失败，请刷新重试'
  }
})

import {useEditorGuard} from '@/js/utils/editor_guard.js'
function hasUnsavedChanges() {return !saved && !!(nameRef.value?.myName || profileRef.value?.myProfile || photoRef.value?.myPhoto || backgroundImageRef.value?.myBackgroundImage || publishRef.value?.description)}
defineExpose({hasUnsavedChanges})
useEditorGuard(hasUnsavedChanges)

async function handleCreate() {
  if (submitting.value) return
  successMessage.value = ''
  const photo = photoRef.value.myPhoto
  const name = nameRef.value.myName?.trim()
  const voice = voiceRef.value.myVoice
  const profile = profileRef.value.myProfile?.trim()
  const backgroundImage = backgroundImageRef.value.myBackgroundImage

  errorMessage.value = ''
  if (!photo) {
    errorMessage.value = '头像不能为空'
  } else if (!name) {
    errorMessage.value = '名字不能为空'
  } else if (publishRef.value.status === 'published' && publishRef.value.visibility === 'public' && !publishRef.value.description.trim()) {
    errorMessage.value = '公开发布需要填写公开简介'
  } else if (!profile) {
    errorMessage.value = '角色介绍不能为空'
  } else if (!backgroundImage) {
    errorMessage.value = '聊天背景不能为空'
  } else {
    submitting.value = true
    const formData = new FormData()
    formData.append('name', name)
    formData.append('voice_id', voice ?? 'none')
    formData.append('public_description', publishRef.value.description.trim())
    formData.append('persona_prompt', profile)
    formData.append('visibility', publishRef.value.visibility)
    formData.append('status', publishRef.value.status)
    formData.append('profile', profile)
    formData.append('photo', base64ToFile(photo, 'photo.png'))
    formData.append('background_image', base64ToFile(backgroundImage, 'background_image.png'))

    try {
      const res = await api.post('/api/create/character/create/', formData)
      const data = res.data
      if (data.result === 'success') {
        saved=true
        await router.push({
          name: 'user-space-index',
          params: {
            user_id: user.id,
          }
        })
      } else {
        errorMessage.value = data.result
      }
    } catch (err) {
      errorMessage.value = err.response?.data?.result || '暂时无法连接，请稍后重试'
    } finally {
      submitting.value = false
    }
  }
}
</script>

<template>
  <div class="flex justify-center">
    <div class="card editor-card">
      <div class="card-body">
        <h3 class="text-lg font-bold my-4">创建角色</h3>
        <Photo ref="photo-ref" />
        <Name ref="name-ref" />
        <Voice ref="voice-ref" :voices="voices" :curVoiceId="curVoiceId" />
        <Profile ref="profile-ref" />
        <BackgroundImage ref="background-image-ref" />

        <PublishSettings ref="publish-ref" />

        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

        <div class="flex justify-center">
          <button @click="handleCreate" class="btn btn-neutral editor-submit" :disabled="submitting">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>